/* Integración incremental por HTTP. La interfaz nunca llama directamente a Ollama ni a SQLite. */
(() => {
  'use strict';
  const UI = window.MatriScopeUI;
  if (!UI) return;
  const {state, render, go, toast, modal, closeModal, esc} = UI;
  const projectIdByName = new Map();
  let lastResult = null;
  let lastResultTitle = '';
  let activeTranslationTrace = null;
  let currentReviewer = '';
  let evaluationRefreshTimer = null;
  let operationInProgress = false;

  async function api(path, options={}) {
    const response = await fetch('/api' + path, options);
    let payload;
    try { payload = await response.json(); } catch { payload = {}; }
    if (!response.ok) {
      const detail = payload.detail;
      throw new Error(typeof detail === 'string' ? detail : `Error HTTP ${response.status}`);
    }
    return payload;
  }
  const jsonOpts = body => ({method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const projectId = () => projectIdByName.get(state.project);

  function liveStatus(text, models) {
    const service=document.getElementById('live-service');
    const model=document.getElementById('live-models');
    const header=document.getElementById('live-environment');
    if(service) service.textContent=text;
    if(model) model.textContent=models;
    if(header) header.textContent=text;
  }

  async function checkHealth() {
    try {
      const health=await api('/health');
      state.availableModels=(health.modelos_instalados||[]).filter(name=>
        !['nomic-embed-text','bge-m3'].includes(name.split(':')[0]));
      if (health.servidor_modelos === 'disponible') {
        liveStatus('API local conectada',`${health.modelos_instalados.length} modelos disponibles`);
      } else {
        liveStatus('API local conectada','Ollama no disponible: RAG detenido');
      }
    } catch {
      liveStatus('API no disponible','Arranca el servicio local');
    }
  }

  async function refreshProjects() {
    const projects=await api('/proyectos');
    projectIdByName.clear();
    for (const item of projects) projectIdByName.set(item.name,item.id);
    state.projects=projects.map(p=>({name:p.name,description:p.description,status:'Registrado'}));
    if (!projectId()) state.project=projects[0]?.name || 'Sin proyecto';
    return projects;
  }

  async function refreshDocuments() {
    if (!projectId()) {state.docs=[];return;}
    const docs=await api('/documentos?project_id='+encodeURIComponent(projectId()));
    state.docs=docs.map(d=>({id:d.id,title:d.filename,author:'Documento del proyecto',
      year:'—',doi:d.doi||'—',license:d.license,type:'Documento',status:'Indexado'}));
  }

  function showError(err) {
    toast(err instanceof Error ? err.message : String(err));
  }

  // Una sola operación por vez. El botón se bloquea inmediatamente; la pantalla
  // de carga aparece si la acción tarda más que una interacción breve.
  async function withOperation(button, title, description, task) {
    if (operationInProgress) return;
    operationInProgress = true;
    const wasDisabled = Boolean(button?.disabled);
    if (button) {
      button.disabled = true;
      button.setAttribute('aria-busy','true');
    }
    const shell = document.querySelector('.app-shell');
    if (shell) shell.inert = true;
    const overlay = document.getElementById('operation-overlay');
    const started = Date.now();
    let elapsedTimer;
    const showTimer = setTimeout(() => {
      if (!overlay) return;
      document.getElementById('operation-title').textContent = title;
      document.getElementById('operation-description').textContent = description;
      document.getElementById('operation-elapsed').textContent = '0 s';
      overlay.hidden = false;
      overlay.setAttribute('aria-hidden','false');
      document.body.classList.add('operation-busy');
      elapsedTimer = setInterval(() => {
        const seconds = Math.floor((Date.now() - started) / 1000);
        document.getElementById('operation-elapsed').textContent = `${seconds} s`;
      },1000);
    },180);
    try {
      return await task();
    } catch(err) {
      showError(err);
      return undefined;
    } finally {
      clearTimeout(showTimer);
      if (elapsedTimer) clearInterval(elapsedTimer);
      if (overlay) {
        overlay.hidden = true;
        overlay.setAttribute('aria-hidden','true');
      }
      document.body.classList.remove('operation-busy');
      if (shell) shell.inert = false;
      if (button?.isConnected) {
        button.disabled = wasDisabled;
        button.removeAttribute('aria-busy');
      }
      operationInProgress = false;
    }
  }

  function appendLivePanel(body, scroll=true) {
    const main=document.getElementById('main-content');
    if(!main)return;
    const old=document.getElementById('live-result-panel');
    old?.remove();
    const panel=document.createElement('section');
    panel.id='live-result-panel';
    panel.className='card';
    panel.style.marginTop='20px';
    panel.innerHTML=body;
    main.appendChild(panel);
    if(scroll)panel.scrollIntoView({behavior:'smooth',block:'nearest'});
  }

  function setLivePage(title, description, content) {
    const main=document.getElementById('main-content');
    if (!main) return;
    main.innerHTML=`<div class="page-heading"><div class="page-heading-left">`+
      `<div class="page-icon" aria-hidden="true">MS</div><div><h1>${esc(title)}</h1>`+
      `<p>${esc(description)}</p></div></div></div>${content}`;
  }

  function displayResponse(result, title, scroll=true) {
    lastResult=result;
    lastResultTitle=title;
    const trace=result.traza_id ? `<code>${esc(result.traza_id)}</code>` : '—';
    const percentage=value=>Math.max(0,Math.min(100,Math.round(Number(value)||0)));
    const translatableSources=(result.fuentes||[]).filter(src=>src.fragmento_id);
    const finishedSources=translatableSources.filter(src=>
      src.traduccion_estado==='traducido'||src.traduccion_estado==='fallo');
    const translatedCount=translatableSources.filter(src=>src.traduccion_estado==='traducido').length;
    const failedCount=finishedSources.length-translatedCount;
    const totalSources=translatableSources.length;
    const overallPercentage=totalSources?percentage(finishedSources.length*100/totalSources):0;
    const overallLabel=finishedSources.length===totalSources?'Procesamiento de fuentes finalizado':
      `Traduciendo fuentes al español · ${finishedSources.length} de ${totalSources} procesadas`;
    const overallProgress=totalSources?
      `<section class="translation-overall" aria-label="Progreso general de traducción">`+
      `<div class="translation-progress-meta"><strong>${esc(overallLabel)}</strong>`+
      `<span>${overallPercentage}%</span></div>`+
      `<div class="translation-progress-track" role="progressbar" `+
      `aria-label="Progreso general de traducción" aria-valuenow="${overallPercentage}" `+
      `aria-valuemin="0" aria-valuemax="100">`+
      `<div class="translation-progress-fill" style="width:${overallPercentage}%"></div></div>`+
      `<p class="subtle"><strong>${translatedCount} de ${totalSources} fuentes traducidas</strong> · `+
      `${failedCount} con error(es). El porcentaje representa fuentes procesadas, `+
      `no traducciones aprobadas.</p></section>`:'';
    const translatedByRef=new Map((result.fuentes||[])
      .filter(src=>src.fragmento_es).map(src=>[src.ref,src.fragmento_es]));
    const citations=(result.fuentes||[]).map(src => {
      const translated=typeof src.fragmento_es==='string'&&src.fragmento_es.trim();
      const phase=src.traduccion_estado||
        (result.traduccion_pendiente?'traduciendo':'no_disponible');
      const advance=src.traduccion_avance ? ` (${esc(src.traduccion_avance)})` : '';
      const errorHint=src.traduccion_error ? ` Motivo: ${esc(src.traduccion_error)}.` : '';
      const rejectedPreview=phase==='fallo'&&src.traduccion_rechazada?
        `<details class="translation-rejected"><summary>Ver traducción rechazada (no validada)</summary>`+
        `<p>${esc(src.traduccion_rechazada)}</p></details>`:'';
      const diff=src.traduccion_detalle;
      const detail=phase==='fallo'&&diff&&
        ((diff.faltantes||[]).length||(diff.adicionales||[]).length)?
        `<div class="translation-difference"><strong>Comparación de valores:</strong>`+
        ((diff.faltantes||[]).length?
          `<p>Valores del original ausentes: ${esc(diff.faltantes.join(', '))}</p>`:'')+
        ((diff.adicionales||[]).length?
          `<p>Valores adicionales en la traducción: ${esc(diff.adicionales.join(', '))}</p>`:'')+
        `</div>`:'';
      const candidates=[state.settings.model,state.settings.fallback,'qwen2.5:3b','llama3.2:3b'];
      const alternate=candidates.find(model=>model&&model!==src.traduccion_modelo&&
        (!state.availableModels?.length||state.availableModels.includes(model)));
      const retry=phase==='fallo'&&alternate&&
        !['ecuacion_pdf_no_interpretable','contenido_tabular_no_traducible']
          .includes(src.traduccion_error)?
        `<div class="live-actions translation-retry"><button class="btn secondary" `+
        `data-live-action="retry-translation" data-fragment-id="${esc(src.fragmento_id)}" `+
        `data-model="${esc(alternate)}">Reintentar con ${esc(alternate)}</button></div>`:'';
      const pct=percentage(src.traduccion_porcentaje??(translated?100:0));
      const progressLabel=phase==='traducido'?'Traducción completada':
        phase==='fallo'?'Traducción detenida':phase==='pendiente'?'En espera de traducción':
        'Traduciendo fragmento';
      const progress=src.fragmento_id?
        `<div class="translation-progress ${phase==='fallo'?'failed':phase==='traducido'?'complete':''}">`+
        `<div class="translation-progress-meta"><span>${esc(progressLabel)}${advance}</span>`+
        `<strong>${pct}%</strong></div>`+
        `<div class="translation-progress-track" role="progressbar" `+
        `aria-label="Traducción ${esc(src.ref)}" aria-valuemin="0" aria-valuemax="100" `+
        `aria-valuenow="${pct}"><div class="translation-progress-fill" `+
        `style="width:${pct}%"></div></div></div>`:'';
      const message=phase==='pendiente'?'Pendiente de traducción al español.':
        phase==='traduciendo'?`Traduciendo este fragmento al español…${advance}`:
        phase==='fallo'&&src.traduccion_error==='ecuacion_pdf_no_interpretable'?
          'El texto del PDF contiene caracteres de una ecuación que no se pueden interpretar con seguridad. Consulta la página original; no se inventó la fórmula.':
        phase==='fallo'&&src.traduccion_error==='contenido_tabular_no_traducible'?
          'El fragmento está formado principalmente por cifras de una tabla o gráfica. Se conserva el original sin pedir a Ollama que traduzca valores numéricos como prosa. Revisa la tabla en el PDF.':
        phase==='fallo'?`La traducción no finalizó o no superó la validación; se conserva el original.${errorHint}`:
        'Traducción no disponible; se muestra el original.';
      return `<li><strong>${esc(src.ref)} ${esc(src.documento)}</strong> · pág. ${esc(src.pagina)}`+
        (src.traduccion_modelo?`<p class="subtle">Modelo de traducción: ${esc(src.traduccion_modelo)}</p>`:'')+
        progress+
        (translated?
          `<p class="source-translation"><strong>${src.traduccion_extracto?'Traducción del pasaje pertinente (fragmento abreviado)':'Traducción al español'}:</strong> ${esc(src.fragmento_es)}</p>`+
          `<details class="comparison-source"><summary>Ver fragmento original (inglés)</summary>`+
          `<p class="subtle">${esc(src.fragmento)}</p></details>`:
          `<p class="subtle">${message}</p>`+
          detail+rejectedPreview+retry+`<p class="subtle">${esc(src.fragmento)}</p>`)+`</li>`;
    }).join('');
    const claims=(result.afirmaciones||[]).map(a=>
      `<li>${esc(a.texto)} <span class="pill teal">${(a.fuentes||[]).map(esc).join(', ')}</span></li>`).join('');
    const comparisonCards=(result.comparacion||[]).map(item=>{
      const doi=typeof item.doi==='string'&&/^10\.\d{4,9}\/[A-Za-z0-9._;()/:+\-]+$/.test(item.doi.trim())
        ? `<a href="https://doi.org/${encodeURIComponent(item.doi.trim())}" target="_blank" rel="noopener noreferrer">Abrir DOI</a>` : '';
      const findings=(item.resultados||[]).map(f=>{
        const fields=[
          ['Energía',f.energia],['Densidad relativa',f.densidad],
          ['Porosidad',f.porosidad],['Tamaño de poro',f.tamano_poro],
          ['Dureza',f.dureza],['Rugosidad',f.rugosidad],
          ['Método',f.metodo==='No especificado en el pasaje'?'—':f.metodo],
          ['Condiciones / alcance',f.condiciones],
        ].filter(([,value])=>value&&value!=='—');
        return `<div class="comparison-fact"><strong>${esc(f.tipo)}</strong>`+
          `<dl class="comparison-metrics">${fields.map(([name,value])=>
            `<div><dt>${esc(name)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl></div>`;
      }).join('');
      return `<article class="comparison-study">`+
        `<header class="comparison-study-header"><div><h5>${esc(item.documento)}</h5>`+
        `<span>${esc(item.ref)} · pág. ${esc(item.pagina)}</span></div>${doi}</header>`+
        `<p class="comparison-variables"><strong>Variables:</strong> `+
        `${esc((item.variables||[]).join(' · ')||'No clasificadas')}</p>`+
        `<div class="comparison-findings">${findings||'<p class="subtle">No se identificó una relación experimental explícita en el pasaje seleccionado.</p>'}</div>`+
        (translatedByRef.has(item.ref)?
          `<p><strong>Traducción al español:</strong> ${esc(translatedByRef.get(item.ref))}</p>`:'')+
        `<details class="comparison-source"><summary>Consultar pasaje original</summary>`+
        `<p>«${esc(item.fragmento)}»</p></details></article>`;
    }).join('');
    const comparisonTable=comparisonCards ? `<h4>Matriz de evidencia entre estudios</h4>`+
      `<div class="comparison-list">${comparisonCards}</div>` : '';
    const coverage=result.cobertura_documental;
    const coverageBox=coverage?.solicitados?.length?
      `<div class="callout"><strong>Cobertura de publicaciones solicitadas:</strong> `+
      `${esc(coverage.recuperados?.join(', ')||'Ninguna')} `+
      (coverage.faltantes?.length?
        `· <strong>Faltan fuentes:</strong> ${esc(coverage.faltantes.join(', '))}.`:
        '· Todos los nombres identificados cuentan con pasajes recuperados; revisa su pertinencia.')+
      `</div>`:'';
    const directQuantitative=result.guardrails==='evidencia_cuantitativa_directa';
    const extractive=result.guardrails==='sintesis_extractiva_cuantitativa';
    const comparing=Boolean(comparisonCards);
    const reasoned=result.guardrails==='comparacion_razonada_validada';
    const hasTranslations=(result.fuentes||[]).some(source=>source.fragmento_es);
    const outsideScope=result.estado==='fuera_de_alcance';
    const backedBySources=result.guardrails==='respuesta_sustituida_por_fuentes';
    const payload = result.abstencion
      ? `<div class="callout">${esc(result.mensaje||'No se encontró evidencia suficiente.')}</div>`
      : `<div class="callout">Estas observaciones requieren comprobación humana en las fuentes.</div>`+
        (directQuantitative ? `<div class="callout"><strong>Relación cuantitativa específica:</strong> `+
          `los valores se asociaron dentro del mismo fragmento documental. `+
          `No se necesitó generar texto con Ollama; comprueba el artículo original.</div>` : '')+
        (extractive ? `<div class="callout"><strong>Resultado extractivo:</strong> `+
          `la síntesis generativa no pasó el control de citas. Los valores mostrados `+
          `se extrajeron de relaciones cuantitativas explícitas en los fragmentos; `+
          `verifica siempre el PDF original.</div>` : '')+
        (comparing ? `<div class="callout"><strong>Comparación documental preliminar:</strong> `+
          `se priorizan resultados explícitos de estudios diferentes. La tabla no equivale a `+
          `una conclusión científica validada.</div>` : '')+
        (reasoned?'<div class="callout"><strong>Razonamiento de Ollama:</strong> '+
          'el modelo comparó los estudios y la respuesta pasó las validaciones de '+
          'citas, cobertura documental y magnitudes. Estas comprobaciones no '+
          'sustituyen la revisión científica de las fuentes originales.</div>':'')+
        (comparing&&backedBySources?'<div class="callout"><strong>Síntesis rechazada:</strong> '+
          'la generación no justificó de forma verificable ambos estudios. '+
          'Se conserva la comparación documental sin atribuirle al modelo '+
          'una conclusión aceptada.</div>':'')+
        (backedBySources&&hasTranslations&&!comparing?
          '<p>La síntesis del modelo fue descartada. Consulta los pasajes traducidos y sus originales en «Fuentes recuperadas».</p>':
          result.texto?`<p style="white-space:pre-wrap">${esc(result.texto)}</p>`:'')+
        (claims?`<h4>Afirmaciones por verificar</h4><ol>${claims}</ol>`:'');
    appendLivePanel(`<div class="card-header"><div class="card-title">${esc(title)}</div></div>`+
      `<div class="card-body">${payload}${coverageBox}${comparisonTable}`+
      `<p class="subtle">Estado: <strong>${esc(result.estado)}</strong> · Modelo de respuesta: `+
      `${esc(result.modelo||'No utilizado (extracción documental)')}`+
      (result.modelo_solicitado?` · Seleccionado: ${esc(result.modelo_solicitado)}`:'')+
      (result.modo_respuesta?` · Modo: ${esc(result.modo_respuesta)}`:'')+
      ` · Caché: ${esc(result.cache||'ninguna')} · Búsquedas: ${esc(result.iteraciones_agente??0)}`+
      (result.intentos_generacion!==undefined && result.intentos_generacion!==null ?
        ` · Intentos de generación: ${esc(result.intentos_generacion)}` : '')+
      ` · Traza: ${trace} · Tiempo: ${esc(result.tiempo_ms??'—')} ms</p>`+
      (result.motivo_validacion ?
        `<div class="callout"><strong>Diagnóstico de validación:</strong> ${esc(result.motivo_validacion)}`+
        `<p class="subtle">La salida del modelo no pasó todos los controles. La evidencia textual permanece disponible para comprobación humana.</p></div>` : '')+
      (outsideScope?'':
        (comparing?`<details class="comparison-full-sources"><summary>Ver todas las fuentes recuperadas</summary>`:
          '<h4>Fuentes recuperadas</h4>')+
        overallProgress+
        (citations?`<ol class="source-list">${citations}</ol>`:'<p>No existen fuentes para mostrar.</p>')+
        (comparing?'</details>':''))+
      (hasTranslations?
        '<p class="subtle">Las traducciones son automáticas. Para citar, comprueba el texto original desplegable.</p>':'')+
      (result.analisis_id?`<div class="live-actions"><button class="btn primary" data-live-action="go-review">`+
        `Revisar afirmaciones y fuentes</button></div>`:'')+
      `<div class="live-feedback"><span>¿Fue útil el resultado?</span>`+
      `<button class="btn secondary" data-live-feedback="true">Sí</button>`+
      `<button class="btn secondary" data-live-feedback="false">No</button></div></div>`,scroll);
  }

  // Una función para la primera traducción y el reintento con otro modelo.
  // Cada porcentaje procede de segmentos confirmados por el servicio local.
  async function translateFragment(source, model, traceId, currentProject, onChange) {
    if(lastResult?.traza_id!==traceId)return;
    let item={...source,fragmento_es:null,traduccion_estado:'traduciendo',
      traduccion_modelo:model,traduccion_porcentaje:0,traduccion_avance:null,
      traduccion_error:null,traduccion_rechazada:null,traduccion_detalle:null};
    onChange(item);
    let spanish=null;
    let diagnostic='';
    let rejectedPreview=null;
    let difference=null;
    for(let request=0;request<14;request++){
      if(lastResult?.traza_id!==traceId)return;
      const controller=new AbortController();
      const timer=setTimeout(()=>controller.abort(),36000);
      let response;
      try{
        response=await api('/traducciones',{
          ...jsonOpts({project_id:currentProject,fragmentos:[source.fragmento_id],
            modelo:model}),signal:controller.signal,
        });
      }catch(err){
        diagnostic=err?.name==='AbortError'?'tiempo_agotado':
          (err?.message||'conexion_no_disponible');
        break;
      }finally{
        clearTimeout(timer);
      }
      if(lastResult?.traza_id!==traceId)return;
      spanish=response.traducciones?.[source.fragmento_id]||null;
      item={...item,traduccion_extracto:Boolean(response.traduccion_extracto)};
      rejectedPreview=response.vista_previa_rechazada||rejectedPreview;
      difference=response.detalle_validacion||difference;
      const progress=response.progreso;
      if(progress){
        const completed=Number(progress.completados)||0;
        const total=Math.max(1,Number(progress.total)||1);
        const percent=progress.porcentaje;
        const pct=Math.max(0,Math.min(100,Math.round(
          percent!==undefined&&Number.isFinite(Number(percent))?
            Number(percent):completed*100/total)));
        item={...item,traduccion_porcentaje:pct,
          traduccion_avance:`${completed} de ${total} segmentos`};
        onChange(item);
      }
      if(spanish||response.estado==='traducido')break;
      diagnostic=response.diagnostico||'';
      if(response.estado==='fallo'||response.estado==='traduccion_parcial')break;
    }
    if(!spanish&&!diagnostic)diagnostic='limite_de_intentos';
    item={...item,fragmento_es:spanish,traduccion_estado:spanish?'traducido':'fallo',
      traduccion_error:spanish?null:diagnostic,traduccion_avance:null,
      traduccion_porcentaje:spanish?100:item.traduccion_porcentaje,
      traduccion_rechazada:spanish?null:rejectedPreview,
      traduccion_detalle:spanish?null:difference};
    onChange(item);
  }

  async function translateEvidence(result, title) {
    const sources=result.fuentes||[];
    const pending=sources.filter(source=>source.fragmento_id);
    if(!pending.length||!projectId())return;
    const traceId=result.traza_id;
    const currentProject=projectId();
    const usedRefs=new Set((result.texto||'').match(/\[F\d+\]/g)||[]);
    for(const claim of result.afirmaciones||[]){
      for(const ref of claim.fuentes||[])usedRefs.add(ref);
    }
    const ordered=[...pending].sort((a,b)=>Number(usedRefs.has(b.ref))-Number(usedRefs.has(a.ref)));
    let translatedSources=sources.map(src=>({...src,
      traduccion_estado:src.fragmento_id?'pendiente':'no_disponible',
      traduccion_porcentaje:0}));
    const translationModel=state.settings.translationModel==='principal'?
      state.settings.model:state.settings.translationModel;
    const repaint=()=>{
      if(lastResult?.traza_id===traceId){
        displayResponse({...result,fuentes:translatedSources,
          traduccion_pendiente:false},title,false);
      }
    };
    activeTranslationTrace=traceId;
    try{
      for(const source of ordered){
        if(lastResult?.traza_id!==traceId)return;
        await translateFragment(source,translationModel,traceId,currentProject,item=>{
          translatedSources=translatedSources.map(src=>src.fragmento_id===source.fragmento_id?
            item:src);
          repaint();
        });
      }
    }finally{
      if(activeTranslationTrace===traceId)activeTranslationTrace=null;
    }
  }

  async function retryTranslation(fragmentId,model) {
    const result=lastResult;
    const traceId=result?.traza_id;
    const source=(result?.fuentes||[]).find(src=>src.fragmento_id===fragmentId);
    if(!source||source.traduccion_estado!=='fallo')return;
    if(activeTranslationTrace===traceId){
      toast('Espera a que termine la traducción actual antes de reintentar.');
      return;
    }
    if(!model||model===source.traduccion_modelo||
       (state.availableModels?.length&&!state.availableModels.includes(model))){
      toast('Selecciona otro modelo instalado para reintentar.');
      return;
    }
    const currentProject=projectId();
    if(!currentProject)return toast('Selecciona un proyecto para traducir.');
    const title=lastResultTitle;
    activeTranslationTrace=traceId;
    try{
      await translateFragment(source,model,traceId,currentProject,item=>{
        if(lastResult?.traza_id!==traceId)return;
        const latest=lastResult;
        const updated=latest.fuentes.map(src=>src.fragmento_id===fragmentId?item:src);
        displayResponse({...latest,fuentes:updated,traduccion_pendiente:false},title,false);
      });
    }finally{
      if(activeTranslationTrace===traceId)activeTranslationTrace=null;
    }
  }

  async function runAnalysis(question, mode) {
    if (!projectId()) throw new Error('Primero crea o selecciona un proyecto de investigación.');
    const result=await api(mode==='map' ? '/mapa-evidencia' : '/consultas',
      jsonOpts({project_id:projectId(),pregunta:question,modelo:state.settings.model,
        modo:mode==='map'&&state.settings.mode==='extractive'?'hybrid':state.settings.mode}));
    closeModal();
    const title=result.estado==='fuera_de_alcance' ? 'Consulta fuera del alcance' :
      mode==='map'?'Mapa de evidencia solicitado':'Resultado de exploración RAG';
    displayResponse({...result,traduccion_pendiente:!!(result.fuentes||[]).length},title);
    void translateEvidence(result,title);
  }

  async function compareModels(question) {
    if (!projectId()) throw new Error('Primero crea o selecciona un proyecto de investigación.');
    const models=[state.settings.model,state.settings.fallback];
    if(models[0]===models[1])throw new Error('Elige dos modelos diferentes para compararlos.');
    const comparison=await api('/comparar-modelos',jsonOpts({
      project_id:projectId(),pregunta:question,modelos:models}));
    const columns=(comparison.resultados||[]).map(entry=>{
      const result=entry.resultado;
      if(!result)return `<article class="model-compare-item"><h4>${esc(entry.modelo_solicitado)}</h4>`+
        `<div class="callout">No pudo ejecutarse: ${esc(entry.error||'Error desconocido')}</div></article>`;
      const sources=(result.fuentes||[]).map(source=>
        `<li>${esc(source.ref||'')} · ${esc(source.documento||'Archivo')} · pág. ${esc(source.pagina??'—')}</li>`).join('');
      const unverified=result.guardrails==='respuesta_sustituida_por_fuentes';
      return `<article class="model-compare-item"><h4>${esc(entry.modelo_solicitado)}</h4>`+
        `<p class="subtle">Ejecutado: ${esc(result.modelo||'No utilizado')} · ${esc(entry.tiempo_ms)} ms</p>`+
        `<p><span class="pill ${unverified||result.abstencion?'warn':'teal'}">${esc(result.estado)}</span>`+
        ` <span class="pill slate">${esc(result.guardrails||'sin_estado')}</span></p>`+
        `<div class="model-compare-answer">${esc(result.texto||result.mensaje||'No hay respuesta verificada.')}</div>`+
        (result.motivo_validacion?`<p class="subtle">Validación: ${esc(result.motivo_validacion)}</p>`:'')+
        (sources?`<details><summary>Fuentes citadas o recuperadas</summary><ol>${sources}</ol></details>`:'')+
        `<p class="subtle">Traza: ${esc(result.traza_id||'—')} · Intentos: ${esc(result.intentos_generacion??0)}</p>`+
        `</article>`;
    }).join('');
    appendLivePanel(`<div class="card-header"><div class="card-title">Comparación de modelos de Ollama</div></div>`+
      `<div class="card-body"><p class="subtle">Pregunta: ${esc(question)}</p>`+
      `<div class="callout">${esc(comparison.nota||'Estas respuestas deben revisarse contra sus fuentes.')}`+
      ` Se usó el modo generativo en ambos modelos, con las mismas políticas de citas.</div>`+
      `<div class="model-compare-grid">${columns}</div></div>`);
  }

  function askForMap() {
    modal('Construir mapa fundamentado',
      `<p class="subtle">Define la pregunta científica. El servicio recuperará fragmentos y propondrá afirmaciones con fuentes.</p>`+
      `<div class="form-field"><label for="live-map-question">Pregunta de investigación</label>`+
      `<textarea id="live-map-question" class="textarea" rows="4" placeholder="¿Qué observaciones reportan los documentos sobre porosidad en 316L fabricado por LPBF?"></textarea></div>`+
      `<div class="callout">Sin documentos indexados o modelos locales disponibles no se generará un análisis.</div>`,
      `<button class="btn secondary" data-action="close-modal">Cancelar</button>`+
      `<button class="btn primary" data-live-action="execute-map">Analizar corpus</button>`,true);
  }

  async function showMetrics() {
    if(state.page!=='operacion')return;
    const m=await api('/metricas');
    appendLivePanel(`<div class="card-header"><div class="card-title">Mediciones reales del servicio</div></div>`+
      `<div class="card-body"><div class="mini-kv">`+
      `<div class="kv"><small>Consultas registradas</small><strong>${m.consultas_registradas}</strong></div>`+
      `<div class="kv"><small>Latencia promedio</small><strong>${m.latencia_promedio_ms??'—'} ms</strong></div>`+
      `<div class="kv"><small>Caché exacta</small><strong>${m.aciertos_cache_exacta}</strong></div>`+
      `<div class="kv"><small>Caché semántica</small><strong>${m.aciertos_cache_semantica}</strong></div>`+
      `<div class="kv"><small>Bloqueos</small><strong>${m.bloqueos_guardrails}</strong></div></div>`+
      `<p class="subtle">${esc(m.nota)}</p></div>`);
  }

  async function showConfiguration() {
    if(state.page!=='configuracion')return;
    const c=await api('/configuracion');
    appendLivePanel(`<div class="card-header"><div class="card-title">Configuración efectiva del backend</div></div>`+
      `<div class="card-body"><p>LLM candidatos: ${c.modelos_lenguaje_candidatos.map(esc).join(' / ')}</p>`+
      `<p>Embeddings activo: <strong>${esc(c.modelo_embeddings_activo)}</strong></p>`+
      `<p>top-k: ${c.top_k}; umbral de recuperación: ${c.umbral_recuperacion}; `+
      `máximo de iteraciones: ${c.max_iteraciones_agente}</p>`+
      `<div class="callout">${esc(c.nota)} Los controles del prototipo no cambian esta configuración de servidor.</div></div>`);
  }

  const statusLabel=claim=>claim.revision?.verdict||'pendiente';
  const approvedCount=a=>(a.resumen_revision?.aceptada||0)+(a.resumen_revision?.corregida||0);

  function citedSources(claim, allSources) {
    return (claim.fuentes||[]).map(ref=>{
      const src=allSources.find(s=>s.ref===ref);
      if(!src)return `<p class="subtle">${esc(ref)} · referencia no encontrada</p>`;
      return `<details class="live-source"><summary>${esc(ref)} ${esc(src.documento)} · página ${esc(src.pagina)}`+
        `</summary><p class="subtle">DOI: ${esc(src.doi||'No declarado')}</p>`+
        `<p>${esc(src.fragmento)}</p></details>`;
    }).join('');
  }

  async function showValidation() {
    if(state.page!=='validacion')return;
    if(!projectId())return setLivePage('Validación científica','Se requiere un proyecto activo.',
      '<div class="card"><div class="card-body">Crea un proyecto y genera un mapa de evidencia antes de revisar.</div></div>');
    const analyses=await api('/analisis?project_id='+encodeURIComponent(projectId()));
    if(state.page!=='validacion')return;
    const totals=analyses.reduce((sum,a)=>{
      for(const key of Object.keys(sum))sum[key]+=(a.resumen_revision?.[key]||0);
      return sum;
    },{pendiente:0,aceptada:0,corregida:0,rechazada:0});
    const cards=analyses.map(a=>{
      const items=a.afirmaciones.map((claim,index)=>{
        const current=claim.revision;
        const formId=`${a.id}-${index}`;
        return `<section class="live-claim"><div class="live-claim-title">`+
          `<strong>Afirmación ${index+1}</strong><span class="pill ${current?.verdict==='rechazada'?'warn':'teal'}">`+
          `${esc(statusLabel(claim))}</span></div>`+
          `<p>${esc(claim.texto)}</p>`+
          (current?.verdict==='corregida'?`<div class="callout"><strong>Texto corregido:</strong> `+
            `${esc(current.corrected_text)}</div>`:'')+
          `<div class="live-sources">${citedSources(claim,a.fuentes)}</div>`+
          (current?`<p class="subtle">Última revisión declarada por ${esc(current.reviewer)}: `+
            `${esc(current.comment)}. Historial: ${claim.historial_revision.length} evento(s).</p>`:'')+
          `<label class="field-label" for="live-comment-${formId}">Justificación obligatoria</label>`+
          `<textarea class="textarea" id="live-comment-${formId}" rows="2" `+
            `placeholder="Explica la evidencia cotejada y las razones de tu decisión."></textarea>`+
          `<label class="field-label" for="live-corrected-${formId}">Redacción corregida (solo al corregir)</label>`+
          `<textarea class="textarea" id="live-corrected-${formId}" rows="2" `+
            `placeholder="Redacta una observación respaldada por los fragmentos citados."></textarea>`+
          `<div class="live-actions">`+
          ['aceptada','corregida','rechazada'].map(verdict=>`<button class="btn secondary" `+
            `data-live-review="${verdict}" data-analysis-id="${esc(a.id)}" `+
            `data-claim-index="${index}">`+
            `${verdict==='aceptada'?'Aceptar':verdict==='corregida'?'Guardar corrección':'Descartar'}</button>`).join('')+
          `</div></section>`;
      }).join('');
      return `<section class="card live-analysis"><div class="card-header"><div class="card-title">`+
        `Análisis del ${esc(a.fecha.slice(0,10))}</div><span class="pill slate">`+
        `${approvedCount(a)} incorporables al informe</span></div><div class="card-body">`+
        `<p><strong>Pregunta:</strong> ${esc(a.pregunta)}</p>`+
        (a.corpus_modificado?'<div class="callout">El corpus ha cambiado desde este análisis. Coteja nuevamente las fuentes.</div>':'')+
        `${items}</div></section>`;
    }).join('');
    setLivePage('Validación científica','Decisiones humanas auditables sobre cada afirmación y sus fuentes.',
      `<div class="card"><div class="card-body"><p>Proyecto activo: <strong>${esc(state.project)}</strong></p>`+
      `<div class="live-review-summary"><span>Pendientes: ${totals.pendiente}</span>`+
      `<span>Aceptadas: ${totals.aceptada}</span><span>Corregidas: ${totals.corregida}</span>`+
      `<span>Rechazadas: ${totals.rechazada}</span></div>`+
      `<label class="field-label" for="live-reviewer">Nombre de quien realiza la revisión</label>`+
      `<input id="live-reviewer" class="input" autocomplete="name" `+
      `value="${esc(currentReviewer)}" placeholder="Nombre completo del revisor">`+
      `<p class="subtle">La identidad es declarada. No hay autenticación de usuarios en esta versión.</p>`+
      `</div></div><div class="live-analysis-list">`+
      (cards||'<div class="card"><div class="card-body">Aún no existen mapas fundamentados. Genera uno desde Mapa de evidencia.</div></div>')+
      `</div>`);
  }

  async function showReports() {
    if(state.page!=='informes')return;
    if(!projectId())return setLivePage('Informes científicos','Se requiere un proyecto activo.',
      '<div class="card"><div class="card-body">Primero crea un proyecto y genera evidencia revisable.</div></div>');
    const analyses=await api('/analisis?project_id='+encodeURIComponent(projectId()));
    if(state.page!=='informes')return;
    const cards=analyses.map(a=>{
      const approved=approvedCount(a);
      return `<article class="card"><div class="card-header"><div class="card-title">`+
        `${esc(a.pregunta)}</div></div><div class="card-body">`+
        `<p class="subtle">Análisis ${esc(a.id)} · ${esc(a.fecha.slice(0,10))}</p>`+
        `<p><strong>${approved}</strong> afirmaciones aceptadas o corregidas · `+
        `${a.resumen_revision.pendiente} pendientes · ${a.resumen_revision.rechazada} descartadas.</p>`+
        (a.corpus_modificado?'<div class="callout">Corpus modificado: verificar vigencia de las fuentes.</div>':'')+
        (approved?`<a class="btn primary" href="/api/informes/${encodeURIComponent(a.id)}.pdf" `+
          `download="matriscope_${esc(a.id)}.pdf">Descargar PDF con evidencia revisada</a>`:
          '<p class="subtle">Todavía no se permite exportar este análisis: falta una revisión favorable.</p>')+
        `</div></article>`;
    }).join('');
    setLivePage('Informes y exportación','Síntesis documentada de los resultados que ya cuentan con revisión humana.',
      `<div class="callout">El PDF solo incluye afirmaciones aceptadas o corregidas con `+
      `sus fuentes documentales; los resultados pendientes y rechazados quedan excluidos.</div>`+
      `<div class="live-analysis-list">${cards||`<div class="card"><div class="card-body">`+
        `Aún no existen análisis para preparar informes.</div></div>`}</div>`);
  }

  const metricNumber=(n,digits=3)=>n===null||n===undefined?'—':Number(n).toFixed(digits);
  function evaluationStatus(status) {
    return ({en_cola:'En cola',ejecutando:'Ejecutando',completada:'Completada',
      completada_con_errores:'Completada con errores',fallida:'Fallida',
      interrumpida:'Interrumpida'})[status]||status;
  }

  function showEvaluationCaseForm() {
    const choices=state.docs.map(doc=>`<label class="live-eval-source-option">`+
      `<input type="checkbox" data-eval-doc value="${esc(doc.id)}">`+
      `<span>${esc(doc.title)}</span></label>`).join('');
    modal('Nuevo caso científico etiquetado',
      `<p class="subtle">La respuesta y sus documentos relevantes deben proceder de una `+
      `lectura humana. El sistema no inventará etiquetas de referencia.</p>`+
      `<div class="form-field"><label for="eval-question">Pregunta científica</label>`+
      `<textarea id="eval-question" rows="3" class="textarea" `+
      `placeholder="¿Qué datos de porosidad en 316L reportan estos artículos?"></textarea></div>`+
      `<div class="form-field"><label>Documentos pertinentes (etiqueta humana)</label>`+
      `${choices||'<p>Primero incorpora documentos al corpus.</p>'}</div>`+
      `<label class="live-eval-source-option"><input id="eval-abstention" type="checkbox">`+
      `<span>Este caso no tiene evidencia suficiente en el corpus</span></label>`+
      `<div class="form-field"><label for="eval-note">Nota del criterio de referencia</label>`+
      `<textarea id="eval-note" rows="3" class="textarea" `+
      `placeholder="Razón de la etiqueta y qué debería cotejar una persona revisora."></textarea></div>`+
      `<div class="callout">Los casos se conservan como registros de referencia. `+
      `Para excluir un caso de futuras ejecuciones, se desactiva sin borrar su historial.</div>`,
      `<button class="btn secondary" data-action="close-modal">Cancelar</button>`+
      `<button class="btn primary" data-live-action="save-evaluation-case">Registrar caso</button>`,true);
  }

  async function showEvaluation() {
    if(state.page!=='evaluacion')return;
    if(evaluationRefreshTimer)clearTimeout(evaluationRefreshTimer);
    if(!projectId())return setLivePage('Evaluación experimental','Se requiere un proyecto activo.',
      '<div class="card"><div class="card-body">Crea un proyecto y carga artículos científicos para comenzar.</div></div>');
    const activeProject=projectId();
    const [cases,runs,config]=await Promise.all([
      api('/evaluaciones/casos?project_id='+encodeURIComponent(activeProject)),
      api('/evaluaciones/ejecuciones?project_id='+encodeURIComponent(activeProject)),
      api('/configuracion'),
    ]);
    if(state.page!=='evaluacion'||projectId()!==activeProject)return;
    const activeCases=cases.filter(c=>c.active);
    const running=runs.some(run=>run.status==='en_cola'||run.status==='ejecutando');
    const casesHtml=cases.map(c=>{
      const names=c.relevant_document_ids.map(id=>state.docs.find(d=>d.id===id)?.title||'Documento retirado');
      return `<div class="live-eval-case"><div><strong>${esc(c.question)}</strong>`+
        `<p class="subtle">${c.expect_abstention?'Caso sin evidencia':names.map(esc).join(' · ')}`+
        ` · ${c.active?'Activo':'Inactivo'}</p>`+
        (c.reference_note?`<p class="subtle">Criterio: ${esc(c.reference_note)}</p>`:'')+
        `</div><button class="btn secondary" data-eval-toggle="${esc(c.id)}" `+
        `data-eval-active="${c.active?'false':'true'}" ${running?'disabled':''}>`+
        `${c.active?'Desactivar':'Reactivar'}</button></div>`;
    }).join('');
    const runsHtml=runs.map(run=>{
      const summary=run.resumen?.combinaciones||[];
      const chartRows=summary.filter(row=>row.recall_at_k!==null&&row.recall_at_k!==undefined)
        .map(row=>{
          const value=Math.max(0,Math.min(1,Number(row.recall_at_k)));
          return `<div class="live-eval-bar-row"><div class="live-eval-bar-label">`+
            `${esc(row.llm)} · ${esc(row.embeddings)}</div>`+
            `<div class="live-eval-bar-track" aria-label="Recall a k: ${metricNumber(value)}">`+
            `<span style="width:${(value*100).toFixed(1)}%"></span></div>`+
            `<strong>${metricNumber(value)}</strong></div>`;
        }).join('');
      const tableRows=summary.map(row=>`<tr><td>${esc(row.llm)}</td><td>${esc(row.embeddings)}</td>`+
        `<td>${metricNumber(row.precision_at_k)}</td><td>${metricNumber(row.recall_at_k)}</td>`+
        `<td>${metricNumber(row.mrr)}</td><td>${metricNumber(row.hit_at_k)}</td>`+
        `<td>${metricNumber(row.latencia_media_ms,0)}</td>`+
        `<td>${row.abstenciones_correctas}/${row.casos_sin_evidencia}</td>`+
        `<td>${row.casos_validos}/${row.casos_evaluados}</td></tr>`).join('');
      return `<section class="card live-eval-run"><div class="card-header">`+
        `<div class="card-title">Experimento del ${esc(run.created_at.slice(0,10))}</div>`+
        `<span class="pill ${run.status==='completada'?'teal':'slate'}">`+
        `${esc(evaluationStatus(run.status))}</span></div><div class="card-body">`+
        `<p class="subtle">ID: ${esc(run.id)} · ${run.completed_tasks}/${run.total_tasks} `+
        `consultas realizadas · ${run.casos_congelados.length} casos congelados</p>`+
        `<div class="live-eval-progress" role="progressbar" aria-valuemin="0" `+
        `aria-valuemax="${run.total_tasks}" aria-valuenow="${run.completed_tasks}">`+
        `<span style="width:${run.total_tasks?Math.round(100*run.completed_tasks/run.total_tasks):0}%"></span></div>`+
        (run.error_message?`<p class="callout">${esc(run.error_message)}</p>`:'')+
        (run.resumen?.advertencia_muestra?`<p class="subtle">${esc(run.resumen.advertencia_muestra)}</p>`:'')+
        (chartRows?`<div class="live-eval-chart"><h4>Recuperación por combinación · Recall@k</h4>`+
          `${chartRows}<p class="subtle">Las combinaciones que comparten embeddings pueden `+
          `obtener el mismo ranking; el LLM influye después, en la generación.</p></div>`:'')+
        (tableRows?`<div class="table-wrap"><table class="data-table live-eval-table"><thead>`+
          `<tr><th>LLM</th><th>Embeddings</th><th>P@k</th><th>R@k</th><th>MRR</th>`+
          `<th>Hit@k</th><th>Lat. ms</th><th>Abst.</th><th>Éxitos</th></tr></thead>`+
          `<tbody>${tableRows}</tbody></table></div>`:'')+
        `<div class="live-actions"><button class="btn secondary" data-eval-details="${esc(run.id)}">`+
        `Ver casos y trazabilidad</button>`+
        (['completada','completada_con_errores'].includes(run.status)?
          `<a class="btn secondary" href="/api/evaluaciones/ejecuciones/${encodeURIComponent(run.id)}.csv" `+
          `download="matriscope_evaluacion_${esc(run.id)}.csv">Exportar CSV</a>`:'')+
        `</div><div id="eval-details-${esc(run.id)}"></div>`+
        `</div></section>`;
    }).join('');
    setLivePage('Evaluación experimental',
      'Comparación controlada de dos LLM y dos embeddings sobre un conjunto etiquetado.',
      `<div class="card"><div class="card-body"><p><strong>Proyecto:</strong> ${esc(state.project)}</p>`+
      `<p class="subtle">LLM: ${config.modelos_lenguaje_candidatos.map(esc).join(' / ')}`+
      ` · Embeddings: ${config.modelos_embeddings_candidatos.map(esc).join(' / ')}`+
      ` · k = ${config.top_k}</p><div class="live-review-summary">`+
      `<span>Casos activos: ${activeCases.length}</span><span>Documentos: ${state.docs.length}</span>`+
      `<span>Experimentos: ${runs.length}</span></div>`+
      `<div class="live-actions"><button class="btn secondary" data-live-action="new-evaluation-case">`+
      `Nuevo caso etiquetado</button><button class="btn primary" `+
      `data-live-action="start-evaluation" ${running||!activeCases.length||!state.docs.length?'disabled':''}>`+
      `Ejecutar comparación 2 × 2</button><button class="btn secondary" `+
      `data-live-action="refresh-evaluation">Actualizar estado</button></div>`+
      `<div class="callout">P@k, Recall@k y MRR miden documentos pertinentes recuperados, `+
      `no la veracidad de las conclusiones. Las citas se evalúan formalmente; `+
      `la exactitud científica necesita revisión humana.</div></div></div>`+
      `<div class="card section-gap"><div class="card-header"><div class="card-title">`+
      `Conjunto de referencia</div></div><div class="card-body">`+
      `${casesHtml||'<p class="subtle">No hay casos etiquetados todavía.</p>'}`+
      `</div></div><div class="section-gap"><h2>Historial de ejecuciones</h2>`+
      `<div class="live-analysis-list">${runsHtml||'<p class="subtle">Todavía no se han ejecutado experimentos.</p>'}`+
      `</div></div>`);
    if(running && state.page==='evaluacion') {
      evaluationRefreshTimer=setTimeout(()=>showEvaluation().catch(showError),4000);
    }
  }

  async function showEvaluationDetails(runId) {
    const container=document.getElementById('eval-details-'+runId);
    if(!container)return;
    container.innerHTML='<p class="subtle">Cargando registros de evaluación…</p>';
    const run=await api('/evaluaciones/ejecuciones/'+encodeURIComponent(runId));
    const cases=new Map(run.casos_congelados.map(item=>[item.id,item]));
    const details=run.resultados.map(item=>{
      const caso=cases.get(item.case_id);
      return `<details class="live-source"><summary>${esc(caso?.question||item.case_id)} `+
        `· ${esc(item.llm_model)} / ${esc(item.embedding_model)}`+
        `${item.error_message?' · ERROR':''}</summary>`+
        `<p><strong>Respuesta:</strong> ${esc(item.answer_text||'Sin respuesta')}</p>`+
        (item.error_message?`<p class="subtle">Error: ${esc(item.error_message)}</p>`:'')+
        `<p class="subtle">Tiempo: ${item.duration_ms} ms · `+
        `Etiquetas: ${(caso?.relevant_document_ids||[]).map(esc).join(', ')||'Sin evidencia'}</p>`+
        `<p class="subtle">Fuentes obtenidas: ${item.fuentes.map(src=>
          `${esc(src.documento)} (p. ${esc(src.pagina)})`).join(' · ')||'Ninguna'}</p>`+
        `</details>`;
    }).join('');
    if(state.page==='evaluacion' && document.getElementById('eval-details-'+runId)){
      document.getElementById('eval-details-'+runId).innerHTML=details||'<p>No hay resultados.</p>';
    }
  }

  async function afterNavigation() {
    try {await refreshDocuments();render();if(state.page==='operacion')await showMetrics();if(state.page==='configuracion')await showConfiguration();
      if(state.page==='validacion')await showValidation();if(state.page==='informes')await showReports();
      if(state.page==='evaluacion')await showEvaluation();}
    catch(err){showError(err);}
  }

  document.addEventListener('click',event=>{
    if(operationInProgress){
      event.preventDefault();event.stopImmediatePropagation();return;
    }
    const details=event.target.closest('[data-eval-details]');
    if(details){
      event.preventDefault();event.stopImmediatePropagation();
      withOperation(details,'Abriendo resultados','Cargando el detalle del experimento.',
        ()=>showEvaluationDetails(details.dataset.evalDetails));return;
    }
    const toggle=event.target.closest('[data-eval-toggle]');
    if(toggle){
      event.preventDefault();event.stopImmediatePropagation();
      const id=toggle.dataset.evalToggle;
      const active=toggle.dataset.evalActive==='true';
      withOperation(toggle,'Actualizando caso','Guardando el estado del caso de evaluación.',async()=>{
        await api('/evaluaciones/casos/'+encodeURIComponent(id),{
        method:'PATCH',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({activo:active}),
        });
        await showEvaluation();
      });
      return;
    }
    const review=event.target.closest('[data-live-review]');
    if(review){
      event.preventDefault();event.stopImmediatePropagation();
      const id=review.dataset.analysisId;
      const index=Number(review.dataset.claimIndex);
      const suffix=`${id}-${index}`;
      const reviewer=document.getElementById('live-reviewer')?.value.trim()||'';
      currentReviewer=reviewer;
      const justification=document.getElementById(`live-comment-${suffix}`)?.value.trim()||'';
      const corrected=document.getElementById(`live-corrected-${suffix}`)?.value.trim()||'';
      const verdict=review.dataset.liveReview;
      if(reviewer.length<2)return toast('Indica el nombre de la persona que revisa.');
      if(justification.length<8)return toast('Escribe una justificación de al menos ocho caracteres.');
      if(verdict==='corregida' && corrected.length<8)return toast('Escribe el texto corregido.');
      if(verdict!=='corregida' && corrected)return toast('Borra el texto corregido si solo aceptarás o descartarás.');
      withOperation(review,'Guardando revisión científica',
        'Registrando tu decisión junto con la justificación y la evidencia.',async()=>{
          await api(`/analisis/${encodeURIComponent(id)}/revisiones`,jsonOpts({indice:index,
            veredicto:verdict,revisor:reviewer,justificacion:justification,
            texto_corregido:corrected}));
          await showValidation();toast('Decisión guardada en el historial de revisión.');
        });
      return;
    }
    const feedback=event.target.closest('[data-live-feedback]');
    if(feedback){
      event.preventDefault();event.stopImmediatePropagation();
      if(!lastResult?.traza_id)return toast('Todavía no existe una traza de respuesta.');
      withOperation(feedback,'Registrando retroalimentación',
        'Guardando tu valoración de la respuesta científica.',async()=>{
          await api('/retroalimentacion',jsonOpts({traza_id:lastResult.traza_id,
            util:feedback.dataset.liveFeedback==='true',comentario:''}));
          toast('Retroalimentación registrada con su traza.');
        });
      return;
    }
    const live=event.target.closest('[data-live-action]');
    if(live){
      event.preventDefault();event.stopImmediatePropagation();
      if(live.dataset.liveAction==='retry-translation'){
        // Mantiene visible la barra en el fragmento durante el reintento.
        void retryTranslation(live.dataset.fragmentId,live.dataset.model).catch(showError);
        return;
      }
      if(live.dataset.liveAction==='clear-query'){
        const query=document.getElementById('explore-query');
        if(query){query.value='';state.exploreQuery='';query.focus();
          document.getElementById('science-query-count').textContent='0 / 1600 caracteres';}
        return;
      }
      if(live.dataset.liveAction==='suggest-query'){
        const query=document.getElementById('explore-query');
        if(query){query.value=live.dataset.question||'';state.exploreQuery=query.value;
          document.getElementById('science-query-count').textContent=`${query.value.length} / 1600 caracteres`;
          query.focus();query.setSelectionRange(query.value.length,query.value.length);}
        return;
      }
      if(live.dataset.liveAction==='compare-models'){
        const question=document.getElementById('explore-query')?.value.trim()||'';
        if(question.length<8)return toast('Escribe una pregunta científica de al menos 8 caracteres.');
        state.exploreQuery=question;
        withOperation(live,'Comparando modelos de Ollama',
          'Ejecutando ambos modelos de forma secuencial y verificando las citas.',
          ()=>compareModels(question));
        return;
      }
      if(live.dataset.liveAction==='execute-map'){
        const question=document.getElementById('live-map-question')?.value.trim()||'';
        if(!question)return toast('Escribe la pregunta que deseas analizar.');
        withOperation(live,'Analizando mapa de evidencia',
          'Recuperando fuentes y contrastando afirmaciones con los modelos locales.',
          ()=>runAnalysis(question,'map'));
      }
      if(live.dataset.liveAction==='go-review'){
        go('validacion');withOperation(live,'Cargando revisiones',
          'Consultando las afirmaciones pendientes.',()=>showValidation());
      }
      if(live.dataset.liveAction==='new-evaluation-case')showEvaluationCaseForm();
      if(live.dataset.liveAction==='refresh-evaluation')withOperation(live,
        'Actualizando evaluación','Consultando el progreso de las pruebas.',()=>showEvaluation());
      if(live.dataset.liveAction==='start-evaluation'){
        withOperation(live,'Iniciando evaluación',
          'Preparando los casos y modelos del experimento.',async()=>{
            await api('/evaluaciones/ejecuciones',jsonOpts({project_id:projectId()}));
            await showEvaluation();toast('Evaluación iniciada con modelos locales.');
          });
      }
      if(live.dataset.liveAction==='save-evaluation-case'){
        const question=document.getElementById('eval-question')?.value.trim()||'';
        const ids=[...document.querySelectorAll('[data-eval-doc]:checked')].map(node=>node.value);
        const abstention=Boolean(document.getElementById('eval-abstention')?.checked);
        const note=document.getElementById('eval-note')?.value.trim()||'';
        if(question.length<8)return toast('El caso requiere una pregunta científica completa.');
        if(abstention&&ids.length)return toast('Si falta evidencia, desmarca los documentos relevantes.');
        if(!abstention&&!ids.length)return toast('Selecciona documentos pertinentes o marca sin evidencia.');
        withOperation(live,'Guardando caso de evaluación',
          'Registrando la pregunta y las etiquetas humanas.',async()=>{
            await api('/evaluaciones/casos',jsonOpts({project_id:projectId(),pregunta:question,
              documentos_relevantes:ids,sin_evidencia:abstention,nota_referencia:note}));
            closeModal();await showEvaluation();toast('Caso de referencia guardado.');
          });
      }
      return;
    }
    const nav=event.target.closest('[data-nav]');
    if(nav){setTimeout(()=>{if(state.page==='operacion')showMetrics().catch(showError);
      if(state.page==='configuracion')showConfiguration().catch(showError);
      if(state.page==='validacion')showValidation().catch(showError);
      if(state.page==='informes')showReports().catch(showError);
      if(state.page==='evaluacion')showEvaluation().catch(showError);},0);return;}
    const item=event.target.closest('[data-action]');
    if(!item)return;
    const action=item.dataset.action;
    const controlled=['submit-project','submit-doc','analysis','explore','help','choose-project','go-validacion'];
    if(!controlled.includes(action))return;
    event.preventDefault();event.stopImmediatePropagation();
    if(action==='analysis')return askForMap();
    if(action==='go-validacion'){
      go('validacion');withOperation(item,'Abriendo validación',
        'Consultando las afirmaciones y sus fuentes.',()=>showValidation());return;
    }
    if(action==='help')return modal('Estado real de MatriScope',
      '<p>La interfaz consume únicamente la API local. La ingesta necesita un modelo de embeddings en Ollama; las consultas y mapas requieren además un modelo de lenguaje instalado.</p>');
    if(action==='choose-project'){
      const project=state.projects[Number(item.dataset.index)];
      if(!project)return;
      state.project=project.name;go('inicio');afterNavigation();return;
    }
    if(action==='submit-project'){
      const name=document.getElementById('project-name')?.value.trim();
      const description=document.getElementById('project-description')?.value||'';
      if(!name)return toast('El proyecto necesita un nombre.');
      withOperation(item,'Creando proyecto',
        'Registrando el nuevo espacio de investigación.',async()=>{
          const project=await api('/proyectos',jsonOpts({name,description}));
          await refreshProjects();state.project=project.name;await refreshDocuments();
          closeModal();go('proyectos');toast('Proyecto registrado en el servicio local.');
        });return;
    }
    if(action==='submit-doc'){
      const file=document.getElementById('doc-file')?.files?.[0];
      if(!file)return toast('Selecciona un documento antes de continuar.');
      if(!projectId())return toast('Primero registra un proyecto.');
      const form=new FormData();
      form.append('project_id',projectId());form.append('licencia',document.getElementById('doc-license')?.value||'');
      form.append('doi',document.getElementById('doc-doi')?.value||'');form.append('archivo',file);
      withOperation(item,'Cargando e indexando el documento',
        `Procesando ${file.name}: extracción de texto, fragmentos y embeddings en Ollama.`,async()=>{
          const result=await api('/documentos',{method:'POST',body:form});
          await refreshDocuments();closeModal();go('corpus');
          toast(`Documento indexado: ${result.fragmentos} fragmentos reales.`);
        });return;
    }
    if(action==='explore'){
      const question=document.getElementById('explore-query')?.value.trim()||'';
      if(!question)return toast('Escribe tu consulta científica.');
      state.exploreQuery=question;
      withOperation(item,'Consultando el corpus científico',
        'Buscando los fragmentos más relevantes y generando una respuesta fundamentada.',
        ()=>runAnalysis(question,'query'));
    }
  },true);

  document.addEventListener('input',event=>{
    if(event.target.id!=='explore-query')return;
    state.exploreQuery=event.target.value;
    const count=document.getElementById('science-query-count');
    if(count)count.textContent=`${event.target.value.length} / 1600 caracteres`;
  });

  // El prototipo original capturaba Enter y mostraba un aviso ficticio. La
  // búsqueda real admite preguntas multilínea y Ctrl/Cmd + Enter para enviar.
  document.addEventListener('keydown',event=>{
    if(event.target.id!=='explore-query')return;
    if(event.key==='Enter'&&(event.ctrlKey||event.metaKey)){
      event.preventDefault();event.stopImmediatePropagation();
      document.querySelector('[data-action="explore"]')?.click();
    }
  },true);

  async function bootstrap() {
    // Descarta los candidatos ficticios de la maqueta: solo mostrar datos de API.
    state.projects=[];state.docs=[];state.project='Sin proyecto';render();
    await checkHealth();
    try {await refreshProjects();await refreshDocuments();render();}
    catch(err){state.projects=[];state.docs=[];render();showError(err);}
  }
  bootstrap();
})();
