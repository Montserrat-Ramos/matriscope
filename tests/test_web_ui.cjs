/* Pruebas sin navegador del contrato de interacción de MatriScope. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const web = path.resolve(__dirname, '../web');
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

function createClassList() {
  const values = new Set();
  return {
    add: value => values.add(value),
    remove: value => values.delete(value),
    contains: value => values.has(value),
  };
}

function setup() {
  const elements = new Map();
  const listeners = {};
  const requests = [];
  const events = [];
  const pending = {upload:null,query:null,comparison:null,translationResponses:[]};
  let explorerButton = null;

  function element(id) {
    if (elements.has(id)) return elements.get(id);
    const value = {
      id, value:'', textContent:'', innerHTML:'', files:[], hidden:true,
      disabled:false, isConnected:true, style:{}, attributes:{}, classList:createClassList(),
      focus(){}, scrollIntoView(){}, setSelectionRange(){},
      remove(){
        elements.delete(this.id);this.isConnected=false;
        if(this.parentElement?.children){
          this.parentElement.children=this.parentElement.children.filter(item=>item!==this);
        }
      },
      setAttribute(name, val){this.attributes[name]=val;},
      removeAttribute(name){delete this.attributes[name];},
      appendChild(child){this.children ??= [];this.children.push(child);},
      closest(){return null;},
    };
    elements.set(id,value);
    return value;
  }

  const shell = {inert:false};
  const doc = {
    body:{classList:createClassList()},
    getElementById(id){
      if(id==='live-result-panel'&&!elements.has(id))return null;
      return element(id);
    },
    querySelector(selector){
      if(selector==='.app-shell')return shell;
      if(selector==='[data-action="explore"]')return explorerButton;
      return null;
    },
    querySelectorAll(){return [];},
    createElement:tag => element(`created-${tag}-${Math.random()}`),
    addEventListener(type, callback, capture=false){
      (listeners[type]??=[]).push({callback,capture:Boolean(capture)});
    },
  };
  element('main-content').appendChild=function(child){
    this.children??=[];this.children.push(child);child.parentElement=this;
    elements.set(child.id,child);
  };
  element('doc-file').files = [{name:'estudio_316L.pdf'}];
  element('doc-license').value = 'CC BY';
  element('doc-doi').value = '10.3390/met11050832';

  const response = (body, status=200) => ({
    ok:status>=200&&status<300, status, json:async()=>body,
  });
  const fetch = async (url,options={}) => {
    requests.push({url,options});
    if(url==='/api/health')return response({servidor_modelos:'disponible',modelos_instalados:['nomic-embed-text:latest','qwen2.5:3b','llama3.2:3b']});
    if(url==='/api/proyectos'&&options.method!=='POST')return response([{id:'p1',name:'Estudio 316L',description:''}]);
    if(url.startsWith('/api/documentos?'))return response([]);
    if(url==='/api/documentos'&&options.method==='POST'){
      return new Promise(resolve=>{
        pending.upload=(body={estado:'indexado',fragmentos:24},status=201)=>resolve(response(body,status));
      });
    }
    if(url==='/api/consultas'&&options.method==='POST'){
      return new Promise(resolve=>{
        pending.query=(body={texto:'Resultado con cita',estado:'pendiente_revision',
          fuentes:[],traza_id:'t1',modelo:'llama3.2:3b',tiempo_ms:1000})=>resolve(response(body));
      });
    }
    if(url==='/api/comparar-modelos'&&options.method==='POST'){
      return new Promise(resolve=>{
        pending.comparison=(body={nota:'Revisión humana obligatoria.',resultados:[
          {modelo_solicitado:'qwen2.5:3b',tiempo_ms:800,resultado:{modelo:'qwen2.5:3b',
            estado:'pendiente_revision',guardrails:'aprobado',texto:'Dato [F1]',
            fuentes:[{ref:'[F1]',documento:'fuente.pdf',pagina:3}],traza_id:'a1'}},
          {modelo_solicitado:'llama3.2:3b',tiempo_ms:1000,resultado:{modelo:'llama3.2:3b',
            estado:'pendiente_revision',guardrails:'aprobado',texto:'Segundo dato [F1]',
            fuentes:[{ref:'[F1]',documento:'fuente.pdf',pagina:3}],traza_id:'a2'}}]})=>
          resolve(response(body));
      });
    }
    if(url==='/api/traducciones'&&options.method==='POST'){
      if(pending.translationResponses.length){
        const next=pending.translationResponses.shift();
        return typeof next==='function'?next(response):response(next);
      }
      return response({traducciones:{'fragmento-1':
        'La densidad de energía fue de 103 J/mm³.'},estado:'traducido'});
    }
    throw new Error(`Solicitud no esperada: ${url}`);
  };
  const storage = new Map();
  const ctx = {
    window:{scrollTo(){}},document:doc,fetch,FormData,AbortController,
    localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},
    setTimeout,clearTimeout,setInterval,clearInterval,
  };
  vm.createContext(ctx);
  for(const name of ['app.js','live.js']){
    vm.runInContext(fs.readFileSync(path.join(web,name),'utf8'),ctx,{filename:name});
  }

  function button(attribute, action, extras={}) {
    const result={...element('btn-'+action),dataset:{},attributes:{},disabled:false,isConnected:true};
    if(attribute==='data-action')result.dataset.action=action;
    if(attribute==='data-live-action')result.dataset.liveAction=action;
    Object.assign(result.dataset,extras);
    result.closest=selector=>selector===`[${attribute}]`?result:null;
    result.click=()=>click(result);
    if(action==='explore')explorerButton=result;
    return result;
  }
  function click(target) {
    const event={target,stopped:false,preventDefault(){},stopImmediatePropagation(){this.stopped=true;}};
    const callbacks=listeners.click||[];
    for(const entry of callbacks.filter(l=>l.capture)){
      entry.callback(event);if(event.stopped)break;
    }
    if(!event.stopped)for(const entry of callbacks.filter(l=>!l.capture)){
      entry.callback(event);if(event.stopped)break;
    }
    events.push(event);
  }
  function keydown(target, key, flags={}) {
    const event={target,key,ctrlKey:false,metaKey:false,stopped:false,...flags,
      preventDefault(){this.prevented=true;},stopImmediatePropagation(){this.stopped=true;}};
    const callbacks=listeners.keydown||[];
    for(const entry of callbacks.filter(l=>l.capture)){
      entry.callback(event);if(event.stopped)break;
    }
    if(!event.stopped)for(const entry of callbacks.filter(l=>!l.capture)){
      entry.callback(event);if(event.stopped)break;
    }
    return event;
  }
  return {ctx,element,shell,requests,pending,button,click,keydown,events};
}

test('dos clics al subir un PDF generan una sola solicitud y un estado de carga',async()=>{
  const ui=setup();
  await wait(20); // bootstrap de proyectos y documentos
  const btn=ui.button('data-action','submit-doc');
  ui.click(btn);
  ui.click(btn);
  assert.equal(ui.requests.filter(r=>r.url==='/api/documentos'&&r.options.method==='POST').length,1);
  assert.equal(btn.disabled,true);
  assert.equal(ui.shell.inert,true);
  await wait(230);
  assert.equal(ui.element('operation-overlay').hidden,false);
  assert.match(ui.element('operation-title').textContent,/Cargando e indexando/);
  ui.pending.upload();
  await wait(25);
  assert.equal(ui.element('operation-overlay').hidden,true);
  assert.equal(ui.shell.inert,false);
  assert.equal(btn.disabled,false);
  assert.match(ui.element('toast').textContent,/24 fragmentos/);
});

test('el nuevo buscador consulta una vez y conserva la pregunta',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  const html=ui.element('main-content').innerHTML;
  assert.match(html,/Investiga tu corpus científico/);
  assert.match(html,/science-query-wrap/);
  assert.match(html,/id="explore-model"/);
  assert.match(html,/id="explore-mode"/);
  assert.match(html,/id="explore-translation-model"/);
  assert.match(html,/value="qwen2\.5:3b" selected/);
  assert.match(html,/value="hybrid" selected/);
  assert.match(html,/Comparar modelos/);
  assert.match(html,/Ctrl \+ Enter/);
  const query=ui.element('explore-query');
  query.value='¿Qué relación existe entre VED y porosidad?';
  const btn=ui.button('data-action','explore');
  const keyboard=ui.keydown(query,'Enter',{ctrlKey:true});
  assert.equal(keyboard.prevented,true);
  ui.click(btn);
  assert.equal(ui.requests.filter(r=>r.url==='/api/consultas').length,1);
  const payload=JSON.parse(ui.requests.find(r=>r.url==='/api/consultas').options.body);
  assert.equal(payload.modelo,'qwen2.5:3b');
  assert.equal(payload.modo,'hybrid');
  assert.equal(btn.disabled,true);
  ui.pending.query();
  await wait(25);
  assert.equal(btn.disabled,false);
  assert.equal(ui.ctx.window.MatriScopeUI.state.exploreQuery,query.value);
  assert.match(ui.element('main-content').children[0].innerHTML,/Resultado con cita/);
});

test('la traducción progresiva usa el modelo seleccionado y termina en español',async()=>{
  const ui=setup();
  await wait(20);
  const state=ui.ctx.window.MatriScopeUI.state;
  state.settings.translationModel='llama3.2:3b';
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.pending.translationResponses=[
    {traducciones:{},estado:'en_progreso',progreso:{completados:1,total:2}},
    {traducciones:{'fragmento-1':'La densidad de energía fue de 103 J/mm³.'},
      estado:'traducido',progreso:{completados:2,total:2}},
  ];
  ui.element('explore-query').value='¿Qué energía documenta el estudio sobre 316L?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({estado:'pendiente_revision',texto:'Energía documentada [F1].',
    fuentes:[{ref:'[F1]',fragmento_id:'fragmento-1',documento:'articulo.pdf',
      pagina:8,fragmento:'The energy density was 103 J/mm3.'}],
    traza_id:'traduccion-progreso',modelo:null,tiempo_ms:2});
  await wait(40);
  const translations=ui.requests.filter(r=>r.url==='/api/traducciones');
  assert.equal(translations.length,2);
  assert.equal(JSON.parse(translations[0].options.body).modelo,'llama3.2:3b');
  assert.equal(JSON.parse(translations[1].options.body).modelo,'llama3.2:3b');
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/La densidad de energía fue de 103/);
  assert.match(html,/Procesamiento de fuentes finalizado/);
  assert.match(html,/1 de 1 fuentes traducidas/);
  assert.match(html,/aria-label="Traducción \[F1\]" aria-valuemin="0" aria-valuemax="100" aria-valuenow="100"/);
  assert.match(html,/class="translation-progress-fill" style="width:100%"/);
});

test('barra de progreso avanza con los segmentos confirmados, sin porcentajes simulados',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  let finish;
  ui.pending.translationResponses=[
    {traducciones:{},estado:'en_progreso',progreso:{completados:1,total:3,porcentaje:33}},
    reply=>new Promise(resolve=>{finish=()=>resolve(reply({
      traducciones:{'fragmento-1':'Traducción correcta.'},estado:'traducido',
      progreso:{completados:3,total:3,porcentaje:100},
    }));}),
  ];
  ui.element('explore-query').value='¿Qué describe el artículo?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({estado:'pendiente_revision',texto:'Dato [F1].',
    fuentes:[{ref:'[F1]',fragmento_id:'fragmento-1',documento:'prueba.pdf',
      pagina:2,fragmento:'Scientific fragment.'}],traza_id:'barra-progreso'});
  await wait(35);
  const progressing=ui.element('main-content').children[0].innerHTML;
  assert.match(progressing,/Traduciendo fragmento/);
  assert.match(progressing,/1 de 3 segmentos/);
  assert.match(progressing,/aria-valuenow="33"/);
  assert.match(progressing,/style="width:33%"/);
  finish();
  await wait(30);
  const finished=ui.element('main-content').children[0].innerHTML;
  assert.match(finished,/Traducción completada/);
  assert.match(finished,/aria-valuenow="100"/);
  assert.match(finished,/style="width:100%"/);
});

test('la barra se detiene si la validación falla y ofrece el diagnóstico',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.pending.translationResponses=[{traducciones:{},estado:'fallo',
    progreso:{completados:1,total:4,porcentaje:25},
    diagnostico:'cifras_alteradas',vista_previa_rechazada:'Valor incorrecto: 500 J/mm³',
    detalle_validacion:{faltantes:['103'],adicionales:['500']}}];
  ui.element('explore-query').value='¿Qué porosidad se observó?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({estado:'pendiente_revision',texto:'Resultado [F1].',
    fuentes:[{ref:'[F1]',fragmento_id:'fragmento-1',documento:'prueba.pdf',
      pagina:2,fragmento:'Porosity at 103 J/mm3.'}],traza_id:'barra-fallo'});
  await wait(30);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/Traducción detenida/);
  assert.match(html,/aria-valuenow="25"/);
  assert.match(html,/style="width:25%"/);
  assert.match(html,/Motivo: cifras_alteradas/);
  assert.match(html,/Ver traducción rechazada \(no validada\)/);
  assert.match(html,/Valor incorrecto: 500 J\/mm³/);
  assert.match(html,/Valores del original ausentes: 103/);
  assert.match(html,/Valores adicionales en la traducción: 500/);
  assert.match(html,/Reintentar con llama3\.2:3b/);
  assert.match(html,/1 con error\(es\)/);
});

test('permite reintentar una fuente fallida con el otro modelo y conserva su evidencia',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.pending.translationResponses=[
    {traducciones:{},estado:'fallo',diagnostico:'cifras_alteradas',
      progreso:{completados:0,total:1,porcentaje:0}},
    {traducciones:{'fragmento-1':'La porosidad registrada fue de 0.38%.'},
      estado:'traducido',progreso:{completados:1,total:1,porcentaje:100}},
  ];
  ui.element('explore-query').value='¿Qué porosidad se registró?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({estado:'pendiente_revision',texto:'Pasaje [F1].',
    fuentes:[{ref:'[F1]',fragmento_id:'fragmento-1',documento:'muestra.pdf',
      pagina:8,fragmento:'The reported porosity was 0.38%.'}],traza_id:'traza-retry'});
  await wait(30);
  let html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/Reintentar con llama3\.2:3b/);
  ui.click(ui.button('data-live-action','retry-translation',{
    fragmentId:'fragmento-1',model:'llama3.2:3b',
  }));
  await wait(35);
  const calls=ui.requests.filter(r=>r.url==='/api/traducciones');
  assert.equal(calls.length,2);
  assert.equal(JSON.parse(calls[0].options.body).modelo,'qwen2.5:3b');
  assert.equal(JSON.parse(calls[1].options.body).modelo,'llama3.2:3b');
  html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/La porosidad registrada fue de 0.38%/);
  assert.match(html,/Modelo de traducción: llama3\.2:3b/);
  assert.match(html,/Ver fragmento original/);
  assert.doesNotMatch(html,/Traducción detenida/);
});

test('advierte cuando falta una de las publicaciones solicitadas',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.element('explore-query').value='¿Equivale el resultado de JMMP al de Metals?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({estado:'sin_evidencia_suficiente',abstencion:true,
    mensaje:'Falta un artículo necesario para la comparación.',
    cobertura_documental:{solicitados:['jmmp','metals'],
      recuperados:['jmmp'],faltantes:['metals']},
    fuentes:[],traza_id:'documento-ausente',modelo:null,tiempo_ms:3});
  await wait(30);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/Cobertura de publicaciones solicitadas/);
  assert.match(html,/Faltan fuentes:<\/strong> metals/);
  assert.match(html,/Falta un artículo necesario para la comparación/);
});

test('muestra razonamiento de Ollama y matriz cuando hybrid valida una comparación',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.element('explore-query').value='¿Equivale JMMP con Metals?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({
    estado:'pendiente_revision',guardrails:'comparacion_razonada_validada',
    texto:'JMMP recomienda un valor [F1].\nMetals reporta un intervalo [F2].\nNo se pueden garantizar resultados equivalentes [F1] [F2].',
    modelo:'qwen2.5:3b',intentos_generacion:1,
    cobertura_documental:{solicitados:['jmmp','metals'],
      recuperados:['jmmp','metals'],faltantes:[]},
    comparacion:[
      {ref:'[F1]',documento:'jmmp.pdf',pagina:15,variables:['Porosidad'],resultados:[],fragmento:'Análisis experimental.'},
      {ref:'[F2]',documento:'metals.pdf',pagina:7,variables:['Porosidad'],resultados:[],fragmento:'Intervalo experimental.'},
    ],
    fuentes:[],traza_id:'comparacion-razonada',tiempo_ms:1234});
  await wait(30);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/Razonamiento de Ollama/);
  assert.match(html,/Modelo de respuesta: /);
  assert.match(html,/qwen2\.5:3b/);
  assert.match(html,/No se pueden garantizar resultados equivalentes/);
  assert.match(html,/Matriz de evidencia entre estudios/);
  assert.match(html,/JMMP|jmmp.pdf/);
});

test('no ofrece reintentar fórmulas ilegibles con otro modelo',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.pending.translationResponses=[{estado:'fallo',traducciones:{},
    diagnostico:'ecuacion_pdf_no_interpretable',
    progreso:{completados:0,total:1,porcentaje:0}}];
  ui.element('explore-query').value='¿Qué ecuación reporta el estudio?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({estado:'pendiente_revision',texto:'Consultar original [F1].',
    fuentes:[{ref:'[F1]',fragmento_id:'fragmento-1',documento:'ecuacion.pdf',
      pagina:5,fragmento:'Ecuación extraída defectuosamente'}],
    traza_id:'formula-corrupta'});
  await wait(30);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/no se pueden interpretar con seguridad/);
  assert.doesNotMatch(html,/Reintentar con llama3\.2:3b/);
});

test('conserva tablas numéricas originales sin intentar volver a traducirlas',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.pending.translationResponses=[{estado:'fallo',traducciones:{},
    diagnostico:'contenido_tabular_no_traducible',
    progreso:{completados:0,total:1,porcentaje:0}}];
  ui.element('explore-query').value='¿Qué datos cuantitativos reporta Metals?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({estado:'pendiente_revision',texto:'Se conserva el original [F1].',
    fuentes:[{ref:'[F1]',fragmento_id:'fragmento-1',documento:'tabla.pdf',
      pagina:12,fragmento:'0 0.03 0.12 34.72 61 ± 25'}],
    traza_id:'tabla-pdf'});
  await wait(30);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/formado principalmente por cifras de una tabla o gráfica/);
  assert.match(html,/0 0\.03 0\.12/);
  assert.doesNotMatch(html,/Reintentar con llama3\.2:3b/);
});

test('no oculta la conclusión documental cuando rechaza una respuesta del modelo',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.element('explore-query').value='¿Equivale JMMP a Metals?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({estado:'pendiente_revision',
    guardrails:'respuesta_sustituida_por_fuentes',
    texto:'No se puede inferir equivalencia entre estos estudios a partir de sus resultados [F1] [F2].',
    comparacion:[{ref:'[F1]',documento:'jmmp.pdf',pagina:15,
      variables:['Energía volumétrica'],resultados:[],fragmento:'El resultado.'}],
    fuentes:[{ref:'[F1]',fragmento_id:'fragmento-1',
      documento:'jmmp.pdf',pagina:15,fragmento:'Enough energy.',
      fragmento_es:'Se requiere energía.'}],
    traza_id:'rechazo-con-traduccion'});
  await wait(30);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/No se puede inferir equivalencia/);
  assert.match(html,/Síntesis rechazada/);
  assert.match(html,/Traducción al español/);
});

test('comparar modelos usa ambos Ollama con citas y sin falsear el modelo',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.element('explore-query').value='¿Qué porosidad reporta el acero 316L?';
  const button=ui.button('data-live-action','compare-models');
  ui.click(button);
  assert.equal(ui.requests.filter(r=>r.url==='/api/comparar-modelos').length,1);
  const body=JSON.parse(ui.requests.find(r=>r.url==='/api/comparar-modelos').options.body);
  assert.deepEqual(body.modelos,['qwen2.5:3b','llama3.2:3b']);
  assert.equal(button.disabled,true);
  ui.pending.comparison();
  await wait(25);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/Comparación de modelos de Ollama/);
  assert.match(html,/qwen2\.5:3b/);
  assert.match(html,/llama3\.2:3b/);
  assert.match(html,/Dato \[F1\]/);
  assert.match(html,/Revisión humana obligatoria/);
  assert.equal(button.disabled,false);
});

test('muestra traducción al español y mantiene el pasaje inglés desplegable',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.element('explore-query').value='¿Qué energía reporta el estudio de 316L?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({
    estado:'pendiente_revision',abstencion:false,
    texto:'Energía documentada [F1].',
    fuentes:[{ref:'[F1]',fragmento_id:'fragmento-1',documento:'articulo.pdf',
      pagina:8,fragmento:'The energy density was 103 J/mm3.'}],
    traza_id:'traduccion-test',modelo:null,tiempo_ms:3,
  });
  await wait(35);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/Traducción al español/);
  assert.match(html,/La densidad de energía fue de 103 J\/mm³/);
  assert.match(html,/Ver fragmento original \(inglés\)/);
  assert.match(html,/The energy density was 103 J\/mm3/);
  assert.equal(ui.requests.filter(r=>r.url==='/api/traducciones').length,1);
});

test('identifica la traducción de extracto y conserva el original íntegro',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.pending.translationResponses=[{
    estado:'traducido',
    traducciones:{'fragmento-1':'Entre 45 y 125 J/mm³ se reportó densidad superior al 99.8 %.'},
    traduccion_extracto:true,
    progreso:{completados:1,total:1,porcentaje:100},
  }];
  ui.element('explore-query').value='¿Qué intervalo reporta Metals?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({estado:'pendiente_revision',texto:'Resultado [F1].',
    fuentes:[{ref:'[F1]',fragmento_id:'fragmento-1',documento:'metals.pdf',
      pagina:6,fragmento:'HEADER FULL. Energy density values between 45 and 125 J/mm3.'}],
    traza_id:'excerpt-translate'});
  await wait(30);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/Traducción del pasaje pertinente \(fragmento abreviado\)/);
  assert.match(html,/HEADER FULL/);
  assert.match(html,/Entre 45 y 125/);
});

test('traduce uno por uno, prioriza la fuente citada y marca el resto sin bloqueo',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.element('explore-query').value='¿Qué relación se reporta para 316L?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({
    estado:'pendiente_revision',abstencion:false,
    texto:'El documento muestra una relación [F1].',
    fuentes:[
      {ref:'[F2]',fragmento_id:'fragmento-2',documento:'otro.pdf',pagina:4,
       fragmento:'This fragment is not translated.'},
      {ref:'[F1]',fragmento_id:'fragmento-1',documento:'citado.pdf',pagina:8,
       fragmento:'The energy density was 103 J/mm3.'},
    ],
    traza_id:'dos-fuentes',modelo:null,tiempo_ms:3,
  });
  await wait(50);
  const requests=ui.requests.filter(r=>r.url==='/api/traducciones');
  assert.equal(requests.length,2);
  assert.deepEqual(JSON.parse(requests[0].options.body).fragmentos,['fragmento-1']);
  assert.deepEqual(JSON.parse(requests[1].options.body).fragmentos,['fragmento-2']);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/La densidad de energía fue de 103 J\/mm³/);
  assert.match(html,/La traducción no finalizó o no superó la validación/);
  assert.doesNotMatch(html,/Traduciendo este fragmento al español/);
});

test('las preguntas fuera del corpus muestran aviso sin fuentes irrelevantes',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.element('explore-query').value='¿Cuánto es 2+2?';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({
    estado:'fuera_de_alcance',abstencion:true,
    mensaje:'Esta pregunta está fuera del alcance de los documentos cargados.',
    fuentes:[],afirmaciones:[],modelo:null,cache:'ninguna',
    iteraciones_agente:0,intentos_generacion:0,
    traza_id:'scope-test',tiempo_ms:1,
  });
  await wait(30);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/Consulta fuera del alcance/);
  assert.match(html,/fuera del alcance de los documentos cargados/);
  assert.doesNotMatch(html,/Fuentes recuperadas/);
  assert.doesNotMatch(html,/No existen fuentes para mostrar/);
});

test('si la carga devuelve 409, la pantalla se libera y el error se informa',async()=>{
  const ui=setup();
  await wait(20);
  const btn=ui.button('data-action','submit-doc');
  ui.click(btn);
  await wait(220);
  assert.equal(ui.element('operation-overlay').hidden,false);
  ui.pending.upload({detail:'Este documento ya está registrado en el proyecto.'},409);
  await wait(25);
  assert.equal(ui.element('operation-overlay').hidden,true);
  assert.equal(ui.shell.inert,false);
  assert.equal(btn.disabled,false);
  assert.match(ui.element('toast').textContent,/ya está registrado/);
});

test('la comparación muestra una matriz legible y escapa contenido del PDF',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  const query=ui.element('explore-query');
  query.value='Compara densidad relativa y porosidad de los artículos';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({
    estado:'pendiente_revision',abstencion:false,
    guardrails:'comparacion_documental',texto:'Se recuperaron dos documentos.',
    fuentes:[],modelo:null,intentos_generacion:0,iteraciones_agente:1,
    comparacion:[{
      documento:'articulo-1.pdf',pagina:6,ref:'[F1]',
      variables:['Energía volumétrica','Densidad relativa'],
      resultados:[{tipo:'intervalo reportado',energia:'45–125 J/mm³',
        densidad:'> 99.8 %',porosidad:'—',
        metodo:'Análisis de imágenes',condiciones:'<script>peligro</script>'}],
      fragmento:'Resultado <script>alert(1)</script> con densidad superior al 99.8%.',
    }],traza_id:'t2',tiempo_ms:12,
  });
  await wait(30);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/Matriz de evidencia entre estudios/);
  assert.match(html,/articulo-1\.pdf/);
  assert.match(html,/comparison-study/);
  assert.match(html,/comparison-metrics/);
  assert.match(html,/Consultar pasaje original/);
  assert.match(html,/45–125 J\/mm³/);
  assert.match(html,/Análisis de imágenes/);
  assert.match(html,/Intentos de generación: 0/);
  assert.match(html,/&lt;script&gt;/);
  assert.doesNotMatch(html,/<script>alert\(1\)<\/script>/);
  assert.doesNotMatch(html,/<script>peligro<\/script>/);
});

test('la comparación muestra porcentajes de porosidad por método sin presentarlos como densidad relativa',async()=>{
  const ui=setup();
  await wait(20);
  ui.ctx.window.MatriScopeUI.go('explorador');
  ui.element('explore-query').value='Compara porosidad óptica y XCT';
  ui.click(ui.button('data-action','explore'));
  ui.pending.query({
    estado:'pendiente_revision',guardrails:'comparacion_documental',
    texto:'Evidencia por método',fuentes:[],
    comparacion:[{documento:'metals-13-00330-v2.pdf',pagina:12,ref:'[F1]',
      variables:['Porosidad'],fragmento:'The measured porosities ...',
      resultados:[
        {tipo:'porosidad de muestras optimizadas',energia:'—',densidad:'—',
          porosidad:'0.0009 %',metodo:'Modelo óptico'},
        {tipo:'porosidad de muestras optimizadas',energia:'—',densidad:'—',
          porosidad:'0.0003 %',metodo:'Modelo XCT'},
      ]}],traza_id:'t3',tiempo_ms:10,
  });
  await wait(30);
  const html=ui.element('main-content').children[0].innerHTML;
  assert.match(html,/0\.0009 %/);
  assert.match(html,/0\.0003 %/);
  assert.match(html,/Modelo óptico/);
  assert.match(html,/Modelo XCT/);
  assert.doesNotMatch(html,/Densidad relativa:\s*0\.0009/);
  assert.match(html,/Ver todas las fuentes recuperadas/);
});
