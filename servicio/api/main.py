"""API REST local de MatriScope. Documentación automática en /docs."""

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from time import perf_counter
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from servicio.config import Settings
from servicio.contexto.ingestion import DocumentError, chunk_pages, extract_pages
from servicio.contexto.translation import EvidenceTranslator
from servicio.datos.ollama import ModelUnavailable, OllamaAdapter
from servicio.datos.sqlite_store import SQLiteStore, now_iso
from servicio.evaluacion.runner import EvaluationError, EvaluationRunner
from servicio.evaluacion.csv_export import export_evaluation_csv
from servicio.guardrails.policy import GuardrailRejected
from servicio.informes.pdf_report import ReportNotReady, create_pdf
from servicio.modelos.gateway import ModelGateway
from servicio.observabilidad.traces import metrics
from servicio.orquestacion.workflows import ScientificWorkflow


class ProjectIn(BaseModel):
    name: str = Field(min_length=3,max_length=90)
    description: str = Field(default='',max_length=2000)


class ScientificRequest(BaseModel):
    project_id: str
    pregunta: str = Field(min_length=8,max_length=1200)
    modelo: str|None = Field(default=None,max_length=120)
    modo: Literal['hybrid','generative','extractive'] = 'hybrid'


class ModelComparisonRequest(BaseModel):
    project_id: str
    pregunta: str = Field(min_length=8,max_length=1200)
    modelos: list[str] = Field(min_length=2,max_length=2)


class TranslationRequest(BaseModel):
    project_id: str
    fragmentos: list[str] = Field(min_length=1,max_length=1)
    modelo: str|None = Field(default=None,max_length=120)


class FeedbackIn(BaseModel):
    traza_id: str
    util: bool
    comentario: str = Field(default='',max_length=1000)


class ClaimReviewIn(BaseModel):
    indice: int = Field(ge=0)
    veredicto: str = Field(pattern='^(aceptada|corregida|rechazada)$')
    revisor: str = Field(min_length=2,max_length=120)
    justificacion: str = Field(min_length=8,max_length=2500)
    texto_corregido: str = Field(default='',max_length=4000)


class EvaluationCaseIn(BaseModel):
    project_id: str
    pregunta: str = Field(min_length=8,max_length=1200)
    documentos_relevantes: list[str] = Field(default_factory=list,max_length=50)
    sin_evidencia: bool = False
    nota_referencia: str = Field(default='',max_length=3000)


class EvaluationCaseStateIn(BaseModel):
    activo: bool


class EvaluationRunIn(BaseModel):
    project_id: str


def create_app(settings=None, store=None, ollama=None):
    settings=settings or Settings()
    store=store or SQLiteStore(settings.data_dir)
    ollama=ollama or OllamaAdapter(settings.ollama_url,settings.model_timeout_seconds)
    gateway=ModelGateway(ollama,settings.llm_simple,settings.llm_complex)
    workflow=ScientificWorkflow(store,gateway,ollama,settings)
    translator=EvidenceTranslator(store,ollama,settings)
    evaluator=EvaluationRunner(store,ollama,settings)
    app=FastAPI(title='MatriScope API',version='0.3.21',
                description='Servicio científico local de ingesta, RAG trazable y mapa de evidencia. '
                            'Las salidas requieren revisión humana.')

    @app.get('/api/health',tags=['Plataforma'])
    def health():
        try:
            models=ollama.models()
            model_status='disponible'
        except ModelUnavailable:
            models=[]
            model_status='no_disponible'
        return {'servicio':'disponible','almacen':'disponible','servidor_modelos':model_status,
                'modelos_instalados':models,'modo':'local',
                'estado':'operativo' if model_status=='disponible' else 'degradado'}

    @app.get('/api/modelos',tags=['RAG'])
    def available_models():
        try:
            installed=ollama.models()
        except ModelUnavailable as exc:
            raise HTTPException(503,str(exc)) from exc
        embeddings={settings.embedding_model.split(':')[0],
                    settings.embedding_candidate.split(':')[0]}
        language_models=[name for name in installed
                         if name.split(':')[0] not in embeddings]
        return {'instalados':language_models,'predeterminado':settings.llm_simple,
                'alternativo':settings.llm_complex,'modo_predeterminado':'hybrid'}

    def require_installed(model_names):
        try:
            installed=set(ollama.models())
        except ModelUnavailable as exc:
            raise HTTPException(503,str(exc)) from exc
        for name in model_names:
            if name not in installed:
                raise HTTPException(422,f'Modelo no instalado en Ollama: {name}. '
                                       f'Instálalo mediante ollama pull {name}.')

    @app.get('/api/proyectos',tags=['Proyectos'])
    def projects():
        return store.projects()

    @app.post('/api/proyectos',status_code=201,tags=['Proyectos'])
    def add_project(payload:ProjectIn):
        return store.add_project(payload.name,payload.description)

    @app.get('/api/documentos',tags=['Documentos'])
    def documents(project_id:str|None=None):
        return store.documents(project_id)

    @app.post('/api/documentos',status_code=201,tags=['Documentos'])
    async def upload_document(project_id:str=Form(...),licencia:str=Form(...),
                              archivo:UploadFile=File(...),doi:str=Form('')):
        if not store.project(project_id):
            raise HTTPException(404,'El proyecto indicado no existe.')
        if not licencia.strip() or licencia.strip().casefold() in {'por verificar','desconocida','sin licencia'}:
            raise HTTPException(422,'Debes revisar y declarar el permiso de uso del documento antes de indexarlo.')
        filename=Path(archivo.filename or '').name
        if not filename or not filename.lower().endswith(('.pdf','.txt','.md')):
            raise HTTPException(422,'Solo se admiten PDF con texto, TXT y Markdown.')
        data=await archivo.read(15*1024*1024+1)
        if len(data)>15*1024*1024:
            raise HTTPException(413,'El documento supera el máximo de 15 MiB.')
        digest=hashlib.sha256(data).hexdigest()
        if any(d['sha256']==digest for d in store.documents(project_id)):
            raise HTTPException(409,'Este documento ya está registrado en el proyecto.')
        try:
            pages=extract_pages(data,filename)
            chunks=chunk_pages(pages)
            if not chunks:
                raise DocumentError('No se obtuvieron fragmentos aprovechables.')
            vectors=[]
            for start in range(0,len(chunks),12):
                vectors.extend(ollama.embed([c['content'] for c in chunks[start:start+12]],
                                            settings.embedding_model))
            if len(vectors)!=len(chunks):
                raise ModelUnavailable('El modelo no generó embeddings para todos los fragmentos.')
        except DocumentError as exc:
            raise HTTPException(422,str(exc)) from exc
        except ModelUnavailable as exc:
            raise HTTPException(503,str(exc)) from exc
        document_id=str(uuid.uuid4())
        meta={'id':document_id,'project_id':project_id,'filename':filename,
              'sha256':digest,'doi':doi.strip(),'license':licencia.strip(),
              'created_at':now_iso(),'pages':len(pages),'chunk_count':len(chunks),
              'embedding_model':settings.embedding_model}
        indexed=[{'id':str(uuid.uuid4()),'document_id':document_id,
                  'project_id':project_id,'page':c['page'],'content':c['content'],
                  'embedding':json.dumps(vector)} for c,vector in zip(chunks,vectors)]
        try:
            store.insert_document(meta,indexed)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409,'Documento duplicado o proyecto no disponible.') from exc
        # Archivo original conservado por identificador generado, no por nombre suministrado.
        document_dir=settings.data_dir/'originales'
        document_dir.mkdir(parents=True,exist_ok=True)
        (document_dir/document_id).write_bytes(data)
        return {'id':document_id,'nombre':filename,'paginas':len(pages),
                'fragmentos':len(chunks),'modelo_embeddings':settings.embedding_model,
                'estado':'indexado','licencia_declarada':licencia.strip()}

    @app.delete('/api/documentos/{document_id}',tags=['Documentos'])
    def delete_document(document_id:str):
        deleted=store.delete_document(document_id)
        if not deleted:
            raise HTTPException(404,'Documento no encontrado.')
        # Los fragmentos y caché se eliminan por referencia en una transacción.
        original=settings.data_dir/'originales'/document_id
        if original.exists():
            original.unlink()
        return {'eliminado':True,'id':document_id,'cache_invalidada':True}

    def process(payload,function_name):
        if not store.project(payload.project_id):
            raise HTTPException(404,'El proyecto indicado no existe.')
        try:
            result=workflow.analyze(payload.project_id,payload.pregunta,function_name,
                                    model_name=payload.modelo,response_mode=payload.modo)
            return {**result,'modelo_solicitado':payload.modelo,
                    'modo_respuesta':payload.modo}
        except GuardrailRejected as exc:
            raise HTTPException(422,str(exc)) from exc
        except ModelUnavailable as exc:
            raise HTTPException(503,str(exc)) from exc

    @app.post('/api/consultas',tags=['RAG'])
    def query(payload:ScientificRequest):
        return process(payload,'consulta')

    @app.post('/api/comparar-modelos',tags=['RAG'])
    def compare_models(payload:ModelComparisonRequest):
        if not store.project(payload.project_id):
            raise HTTPException(404,'El proyecto indicado no existe.')
        if len(set(payload.modelos))!=2 or any(not name.strip() for name in payload.modelos):
            raise HTTPException(422,'Selecciona dos modelos diferentes.')
        require_installed(payload.modelos)
        results=[]
        # Ollama se ejecuta secuencialmente para no agotar la memoria local.
        for name in payload.modelos:
            started=perf_counter()
            try:
                result=workflow.analyze(payload.project_id,payload.pregunta,'consulta',
                                        model_name=name,response_mode='generative')
                results.append({'modelo_solicitado':name,
                                'tiempo_ms':round((perf_counter()-started)*1000),
                                'resultado':{**result,'modo_respuesta':'generative',
                                             'modelo_solicitado':name}})
            except (GuardrailRejected,ModelUnavailable) as exc:
                results.append({'modelo_solicitado':name,
                                'tiempo_ms':round((perf_counter()-started)*1000),
                                'error':str(exc),'resultado':None})
        return {'modo':'generative','pregunta':payload.pregunta,'resultados':results,
                'nota':('Las dos respuestas usan el mismo corpus y deben '
                        'verificarse con las fuentes. Las citas válidas no '
                        'equivalen a una conclusión científica aprobada.')}

    @app.post('/api/traducciones',tags=['RAG'])
    def translate_sources(payload:TranslationRequest):
        if not store.project(payload.project_id):
            raise HTTPException(404,'El proyecto indicado no existe.')
        try:
            return translator.translate(payload.project_id,payload.fragmentos,
                                        model_name=payload.modelo)
        except LookupError as exc:
            raise HTTPException(404,str(exc)) from exc
        except ModelUnavailable as exc:
            raise HTTPException(503,str(exc)) from exc

    @app.post('/api/mapa-evidencia',tags=['RAG'])
    def evidence_map(payload:ScientificRequest):
        result=process(payload,'mapa-evidencia')
        if not result.get('abstencion') and result.get('afirmaciones'):
            saved=store.save_analysis(payload.project_id,payload.pregunta,result)
            return {**result,'analisis_id':saved['id']}
        return {**result,'analisis_id':None}

    @app.get('/api/analisis',tags=['Revisión científica'])
    def list_analyses(project_id:str|None=None):
        return store.analyses(project_id)

    @app.get('/api/analisis/{analysis_id}',tags=['Revisión científica'])
    def get_analysis(analysis_id:str):
        result=store.analysis(analysis_id)
        if result is None:
            raise HTTPException(404,'Análisis no encontrado.')
        return result

    @app.post('/api/analisis/{analysis_id}/revisiones',tags=['Revisión científica'])
    def review_claim(analysis_id:str,payload:ClaimReviewIn):
        try:
            return store.review_claim(analysis_id,payload.indice,payload.veredicto,
                                      payload.revisor,payload.justificacion,payload.texto_corregido)
        except LookupError as exc:
            raise HTTPException(404,str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc

    @app.get('/api/informes/{analysis_id}.pdf',tags=['Informes'])
    def download_report(analysis_id:str):
        analysis=store.analysis(analysis_id)
        if not analysis:
            raise HTTPException(404,'Análisis no encontrado.')
        project=store.project(analysis['project_id'])
        if not project:
            raise HTTPException(409,'El proyecto original ya no está disponible.')
        selected=[claim for claim in analysis['afirmaciones']
                  if (claim.get('revision') or {}).get('verdict') in {'aceptada','corregida'}]
        cited_refs={ref for claim in selected for ref in claim.get('fuentes',[])}
        cited_sources=[src for src in analysis['fuentes'] if src.get('ref') in cited_refs]
        if any(not store.document(src.get('documento_id')) for src in cited_sources):
            raise HTTPException(409,'No se puede exportar: una fuente citada ya fue retirada del corpus.')
        try:
            pdf=create_pdf(analysis,project)
        except ReportNotReady as exc:
            raise HTTPException(409,str(exc)) from exc
        return Response(content=pdf,media_type='application/pdf',headers={
            'Content-Disposition':f'attachment; filename="matriscope_{analysis_id}.pdf"',
            'Cache-Control':'no-store'})

    @app.post('/api/retroalimentacion',status_code=201,tags=['Evaluación'])
    def feedback(payload:FeedbackIn):
        if not any(row['id']==payload.traza_id for row in store.traces()):
            raise HTTPException(404,'La traza indicada no existe o ya fue archivada.')
        return store.feedback(payload.traza_id,payload.util,payload.comentario)

    @app.get('/api/metricas',tags=['Evaluación'])
    def get_metrics():
        return metrics(store)

    @app.get('/api/configuracion',tags=['Plataforma'])
    def configuration():
        return {'modo':'local','ollama_url':settings.ollama_url,
                'modelos_lenguaje_candidatos':[settings.llm_simple,settings.llm_complex],
                'modelos_embeddings_candidatos':[settings.embedding_model,settings.embedding_candidate],
                'modelo_embeddings_activo':settings.embedding_model,'top_k':settings.top_k,
                'umbral_recuperacion':settings.min_similarity,
                'umbral_cache_semantica':settings.cache_similarity,
                'expiracion_cache_segundos':settings.cache_ttl_seconds,
                'max_iteraciones_agente':settings.agent_max_iterations,
                'nota':'La selección final de modelos y umbrales requiere comparación experimental; estos valores son provisionales.'}

    @app.get('/api/evaluaciones/casos',tags=['Evaluación experimental'])
    def evaluation_cases(project_id:str):
        if not store.project(project_id):
            raise HTTPException(404,'El proyecto indicado no existe.')
        return store.evaluation_cases(project_id)

    @app.post('/api/evaluaciones/casos',status_code=201,tags=['Evaluación experimental'])
    def add_evaluation_case(payload:EvaluationCaseIn):
        try:
            return store.add_evaluation_case(payload.project_id,payload.pregunta,
                payload.documentos_relevantes,payload.sin_evidencia,payload.nota_referencia)
        except LookupError as exc:
            raise HTTPException(404,str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc

    @app.patch('/api/evaluaciones/casos/{case_id}',tags=['Evaluación experimental'])
    def update_evaluation_case(case_id:str,payload:EvaluationCaseStateIn):
        try:
            return store.set_evaluation_case_active(case_id,payload.activo)
        except LookupError as exc:
            raise HTTPException(404,str(exc)) from exc

    @app.post('/api/evaluaciones/ejecuciones',status_code=202,tags=['Evaluación experimental'])
    def start_evaluation(payload:EvaluationRunIn):
        try:
            return evaluator.start(payload.project_id)
        except ModelUnavailable as exc:
            raise HTTPException(503,str(exc)) from exc
        except EvaluationError as exc:
            raise HTTPException(409,str(exc)) from exc

    @app.get('/api/evaluaciones/ejecuciones',tags=['Evaluación experimental'])
    def evaluation_runs(project_id:str):
        if not store.project(project_id):
            raise HTTPException(404,'El proyecto indicado no existe.')
        return store.evaluation_runs(project_id)

    @app.get('/api/evaluaciones/ejecuciones/{run_id}.csv',tags=['Evaluación experimental'])
    def evaluation_export(run_id:str):
        result=store.evaluation_run(run_id,with_results=True)
        if not result:
            raise HTTPException(404,'La ejecución indicada no existe.')
        try:
            content=export_evaluation_csv(result)
        except ValueError as exc:
            raise HTTPException(409,str(exc)) from exc
        return Response(content=content,media_type='text/csv; charset=utf-8',headers={
            'Content-Disposition':f'attachment; filename="matriscope_evaluacion_{run_id}.csv"',
            'Cache-Control':'no-store'})

    @app.get('/api/evaluaciones/ejecuciones/{run_id}',tags=['Evaluación experimental'])
    def evaluation_run(run_id:str):
        result=store.evaluation_run(run_id,with_results=True)
        if not result:
            raise HTTPException(404,'La ejecución indicada no existe.')
        return result

    web=Path(__file__).resolve().parents[2]/'web'
    if web.is_dir():
        app.mount('/',StaticFiles(directory=str(web),html=True),name='web')
    return app


app=create_app()

