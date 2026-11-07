"""C7: almacén local de corpus, vectores, proyectos, caché y auditoría.

La búsqueda vectorial de esta primera versión es coseno sobre embeddings
persistidos en SQLite. Su interfaz permite sustituirla por Chroma sin cambiar
las capas de aplicación; la comparación de motores queda para la evaluación.
"""

import json
import math
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(float(x)*float(y) for x,y in zip(a,b))
    na = math.sqrt(sum(float(x)*float(x) for x in a))
    nb = math.sqrt(sum(float(x)*float(x) for x in b))
    return dot/(na*nb) if na and nb else -1.0


class SQLiteStore:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.directory = directory
        self.db = sqlite3.connect(directory/'matriscope.sqlite3',check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.lock=threading.RLock()
        with self.lock, self.db:
            self.db.executescript('''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
                created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                filename TEXT NOT NULL, sha256 TEXT NOT NULL, doi TEXT, license TEXT NOT NULL,
                created_at TEXT NOT NULL, pages INTEGER NOT NULL, chunk_count INTEGER NOT NULL,
                embedding_model TEXT NOT NULL, UNIQUE(project_id, sha256));
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                project_id TEXT NOT NULL, page INTEGER NOT NULL, content TEXT NOT NULL,
                embedding TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cache (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL, corpus_fingerprint TEXT NOT NULL,
                function_name TEXT NOT NULL, question TEXT NOT NULL, question_vector TEXT NOT NULL,
                output_json TEXT NOT NULL, created_epoch REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY, project_id TEXT, status TEXT NOT NULL,
                function_name TEXT, model TEXT, cache TEXT, guardrail TEXT,
                iterations INTEGER NOT NULL, duration_ms INTEGER NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY, trace_id TEXT NOT NULL REFERENCES traces(id),
                useful INTEGER NOT NULL, comment TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                trace_id TEXT NOT NULL REFERENCES traces(id), question TEXT NOT NULL,
                corpus_fingerprint TEXT NOT NULL, result_json TEXT NOT NULL,
                created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS claim_reviews (
                id TEXT PRIMARY KEY, analysis_id TEXT NOT NULL REFERENCES analyses(id),
                claim_index INTEGER NOT NULL, verdict TEXT NOT NULL,
                corrected_text TEXT NOT NULL, comment TEXT NOT NULL,
                reviewer TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_analyses_project ON analyses(project_id,created_at);
            CREATE INDEX IF NOT EXISTS idx_reviews_analysis ON claim_reviews(analysis_id,claim_index);
            CREATE TABLE IF NOT EXISTS evaluation_cases (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                question TEXT NOT NULL, relevant_document_ids TEXT NOT NULL,
                expect_abstention INTEGER NOT NULL, reference_note TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_eval_cases_project
                ON evaluation_cases(project_id,active,created_at);
            CREATE TABLE IF NOT EXISTS evaluation_runs (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                status TEXT NOT NULL, corpus_fingerprint TEXT NOT NULL,
                config_json TEXT NOT NULL, cases_snapshot_json TEXT NOT NULL,
                completed_tasks INTEGER NOT NULL, total_tasks INTEGER NOT NULL,
                summary_json TEXT NOT NULL, error_message TEXT NOT NULL,
                created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT);
            CREATE TABLE IF NOT EXISTS evaluation_results (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES evaluation_runs(id),
                case_id TEXT NOT NULL, llm_model TEXT NOT NULL,
                embedding_model TEXT NOT NULL, metrics_json TEXT NOT NULL,
                answer_text TEXT NOT NULL, sources_json TEXT NOT NULL,
                error_message TEXT NOT NULL, duration_ms INTEGER NOT NULL,
                UNIQUE(run_id,case_id,llm_model,embedding_model));
            CREATE INDEX IF NOT EXISTS idx_eval_results_run ON evaluation_results(run_id);
            CREATE TABLE IF NOT EXISTS evaluation_vectors (
                chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
                embedding_model TEXT NOT NULL, model_digest TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                PRIMARY KEY(chunk_id,embedding_model,model_digest));
            ''')
            # En ejecución local, un reinicio interrumpe tareas en memoria: nunca
            # presentar una ejecución huérfana como si siguiera progresando.
            self.db.execute('''UPDATE evaluation_runs SET status='interrumpida',
                error_message='El proceso se reinició mientras la evaluación estaba en curso.',
                finished_at=? WHERE status IN ('en_cola','ejecutando')''',(now_iso(),))

    def _all(self, query, params=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(query,params).fetchall()]

    def add_project(self,name,description):
        item={'id':str(uuid.uuid4()),'name':name.strip(),'description':description.strip(),'created_at':now_iso()}
        with self.lock, self.db:
            self.db.execute('INSERT INTO projects VALUES(:id,:name,:description,:created_at)',item)
        return item

    def projects(self):
        return self._all('SELECT * FROM projects ORDER BY created_at DESC')

    def project(self,project_id):
        items=self._all('SELECT * FROM projects WHERE id=?',(project_id,))
        return items[0] if items else None

    def documents(self,project_id=None):
        if project_id:
            return self._all('SELECT * FROM documents WHERE project_id=? ORDER BY created_at DESC',(project_id,))
        return self._all('SELECT * FROM documents ORDER BY created_at DESC')

    def document(self,doc_id):
        items=self._all('SELECT * FROM documents WHERE id=?',(doc_id,))
        return items[0] if items else None

    def scope_samples(self,project_id,limit=4):
        """Breves muestras de documentos diferentes para clasificar alcance."""
        return self._all('''SELECT d.filename,c.content FROM documents d
            JOIN chunks c ON c.document_id=d.id
            WHERE d.project_id=? AND c.id=(
                SELECT c2.id FROM chunks c2 WHERE c2.document_id=d.id
                ORDER BY c2.page,c2.id LIMIT 1)
            ORDER BY d.created_at DESC,d.id LIMIT ?''',(project_id,limit))

    def chunks_by_ids(self,project_id,fragment_ids):
        """Solo permite traducir fragmentos realmente indexados en el proyecto."""
        if not fragment_ids:
            return []
        slots=','.join('?' for _ in fragment_ids)
        found=self._all(f'''SELECT id,content FROM chunks
            WHERE project_id=? AND id IN ({slots})''',
            (project_id,*fragment_ids))
        by_id={row['id']:row for row in found}
        return [by_id[fragment_id] for fragment_id in dict.fromkeys(fragment_ids)
                if fragment_id in by_id]

    def insert_document(self,meta,chunks):
        with self.lock, self.db:
            self.db.execute('''INSERT INTO documents
                (id,project_id,filename,sha256,doi,license,created_at,pages,chunk_count,embedding_model)
                VALUES (:id,:project_id,:filename,:sha256,:doi,:license,:created_at,:pages,:chunk_count,:embedding_model)''',meta)
            self.db.executemany('''INSERT INTO chunks
                (id,document_id,project_id,page,content,embedding)
                VALUES (:id,:document_id,:project_id,:page,:content,:embedding)''',chunks)
            self.db.execute('DELETE FROM cache WHERE project_id=?',(meta['project_id'],))

    def delete_document(self,doc_id):
        target=self.document(doc_id)
        if not target:return None
        with self.lock,self.db:
            self.db.execute('DELETE FROM documents WHERE id=?',(doc_id,))
            self.db.execute('DELETE FROM cache WHERE project_id=?',(target['project_id'],))
        return target

    def fingerprint(self,project_id):
        docs=self._all('SELECT sha256,embedding_model FROM documents WHERE project_id=? ORDER BY sha256',(project_id,))
        return json.dumps(docs,sort_keys=True)

    def vector_search(self,project_id,vector,limit,threshold,document_ids=None):
        if document_ids is not None and not document_ids:
            return []
        extra=''
        values=[project_id]
        if document_ids is not None:
            ids=sorted(set(document_ids))
            extra=' AND c.document_id IN ('+','.join('?' for _ in ids)+')'
            values.extend(ids)
        rows=self._all('''SELECT c.id,c.document_id,c.page,c.content,c.embedding,
                          d.filename,d.doi,d.license
                          FROM chunks c JOIN documents d ON c.document_id=d.id
                          WHERE c.project_id=?'''+extra,tuple(values))
        found=[]
        for r in rows:
            similarity=cosine(vector,json.loads(r.pop('embedding')))
            if similarity>=threshold:
                r['similarity']=round(similarity,6)
                found.append(r)
        return sorted(found,key=lambda item:item['similarity'],reverse=True)[:limit]

    def all_cache(self,project_id,function_name,fingerprint):
        return self._all('SELECT * FROM cache WHERE project_id=? AND function_name=? AND corpus_fingerprint=?',
                         (project_id,function_name,fingerprint))

    def write_cache(self,project_id,function_name,fingerprint,question,vector,result,epoch):
        with self.lock,self.db:
            self.db.execute('''INSERT INTO cache VALUES (?,?,?,?,?,?,?,?)''',
                (str(uuid.uuid4()),project_id,fingerprint,function_name,question,
                 json.dumps(vector),json.dumps(result,ensure_ascii=False),epoch))

    def record_trace(self,trace):
        with self.lock,self.db:
            self.db.execute('''INSERT INTO traces VALUES
                (:id,:project_id,:status,:function_name,:model,:cache,:guardrail,
                 :iterations,:duration_ms,:created_at)''',trace)

    def traces(self):
        return self._all('SELECT * FROM traces ORDER BY created_at DESC LIMIT 200')

    def feedback(self,trace_id,useful,comment):
        item={'id':str(uuid.uuid4()),'trace_id':trace_id,'useful':int(useful),
              'comment':comment,'created_at':now_iso()}
        with self.lock,self.db:
            self.db.execute('INSERT INTO feedback VALUES (:id,:trace_id,:useful,:comment,:created_at)',item)
        return item

    def feedback_count(self):
        return self._all('SELECT useful,COUNT(*) AS n FROM feedback GROUP BY useful')

    def save_analysis(self,project_id,question,result):
        """Congela el resultado propuesto para una revisión humana posterior.

        Nunca da por validadas afirmaciones generadas por el modelo.
        """
        if result.get('abstencion') or not result.get('afirmaciones'):
            raise ValueError('No existe un mapa con afirmaciones que guardar.')
        if not result.get('traza_id') or not result.get('fuentes'):
            raise ValueError('El análisis necesita una traza y fuentes documentales.')
        item={'id':str(uuid.uuid4()),'project_id':project_id,'trace_id':result['traza_id'],
              'question':question,'corpus_fingerprint':self.fingerprint(project_id),
              'result_json':json.dumps(result,ensure_ascii=False), 'created_at':now_iso()}
        with self.lock,self.db:
            self.db.execute('''INSERT INTO analyses
                (id,project_id,trace_id,question,corpus_fingerprint,result_json,created_at)
                VALUES (:id,:project_id,:trace_id,:question,:corpus_fingerprint,:result_json,:created_at)''',item)
        return self.analysis(item['id'])

    def analysis(self,analysis_id):
        with self.lock:
            rows=self._all('SELECT * FROM analyses WHERE id=?',(analysis_id,))
            if not rows:
                return None
            row=rows[0]
            events=self._all('''SELECT * FROM claim_reviews WHERE analysis_id=?
                                  ORDER BY rowid ASC''',(analysis_id,))
        original=json.loads(row.pop('result_json'))
        claims=[dict(item) for item in original.get('afirmaciones',[])]
        for index,claim in enumerate(claims):
            related=[event for event in events if event['claim_index']==index]
            claim['revision']=related[-1] if related else None
            claim['historial_revision']=related
        counts={'pendiente':0,'aceptada':0,'corregida':0,'rechazada':0}
        for claim in claims:
            counts[claim['revision']['verdict'] if claim['revision'] else 'pendiente']+=1
        return {'id':row['id'],'project_id':row['project_id'],
                'traza_id':row['trace_id'],'pregunta':row['question'],
                'fecha':row['created_at'],'corpus_modificado':
                self.fingerprint(row['project_id'])!=row['corpus_fingerprint'],
                'afirmaciones':claims,'fuentes':original.get('fuentes',[]),
                'modelo':original.get('modelo'),'resumen_revision':counts}

    def analyses(self,project_id=None):
        if project_id:
            rows=self._all('SELECT id FROM analyses WHERE project_id=? ORDER BY created_at DESC,rowid DESC',
                           (project_id,))
        else:
            rows=self._all('SELECT id FROM analyses ORDER BY created_at DESC,rowid DESC')
        return [self.analysis(row['id']) for row in rows]

    def review_claim(self,analysis_id,index,verdict,reviewer,comment,corrected_text=''):
        """Registra un evento auditable; conserva todas las decisiones anteriores."""
        allowed={'aceptada','corregida','rechazada'}
        if verdict not in allowed:
            raise ValueError('Decisión de revisión desconocida.')
        if not isinstance(index,int) or isinstance(index,bool) or index<0:
            raise ValueError('Índice de afirmación inválido.')
        if len(reviewer.strip())<2 or len(comment.strip())<8:
            raise ValueError('La revisión necesita revisor y justificación suficiente.')
        if verdict=='corregida' and len(corrected_text.strip())<8:
            raise ValueError('Una corrección necesita el texto corregido.')
        if verdict!='corregida' and corrected_text.strip():
            raise ValueError('El texto corregido solo se admite al corregir.')
        with self.lock,self.db:
            item=self.analysis(analysis_id)
            if not item:
                raise LookupError('Análisis no encontrado.')
            if index>=len(item['afirmaciones']):
                raise ValueError('La afirmación indicada no existe en este análisis.')
            event={'id':str(uuid.uuid4()),'analysis_id':analysis_id,'claim_index':index,
                   'verdict':verdict,'corrected_text':corrected_text.strip(),
                   'comment':comment.strip(),'reviewer':reviewer.strip(),'created_at':now_iso()}
            self.db.execute('''INSERT INTO claim_reviews
                (id,analysis_id,claim_index,verdict,corrected_text,comment,reviewer,created_at)
                VALUES (:id,:analysis_id,:claim_index,:verdict,:corrected_text,:comment,:reviewer,:created_at)''',event)
        return self.analysis(analysis_id)

    # Evaluación experimental (fase 3). El conjunto etiquetado permanece
    # separado de los datos generados por los modelos.
    def add_evaluation_case(self,project_id,question,relevant_document_ids,
                            expect_abstention=False,reference_note=''):
        if not self.project(project_id):
            raise LookupError('Proyecto no encontrado.')
        ids=list(dict.fromkeys(relevant_document_ids))
        available={item['id'] for item in self.documents(project_id)}
        if not 8<=len(question.strip())<=1200:
            raise ValueError('La pregunta necesita entre 8 y 1200 caracteres.')
        if expect_abstention and ids:
            raise ValueError('Los casos sin evidencia no deben etiquetar documentos pertinentes.')
        if not expect_abstention and not ids:
            raise ValueError('Etiqueta al menos un documento pertinente, o marca sin evidencia.')
        if any(doc_id not in available for doc_id in ids):
            raise ValueError('Hay documentos etiquetados fuera del proyecto o no disponibles.')
        item={'id':str(uuid.uuid4()),'project_id':project_id,'question':question.strip(),
              'relevant_document_ids':json.dumps(ids),
              'expect_abstention':int(bool(expect_abstention)),
              'reference_note':reference_note.strip(),'active':1,'created_at':now_iso()}
        with self.lock,self.db:
            self.db.execute('''INSERT INTO evaluation_cases
                (id,project_id,question,relevant_document_ids,expect_abstention,
                 reference_note,active,created_at)
                 VALUES (:id,:project_id,:question,:relevant_document_ids,
                 :expect_abstention,:reference_note,:active,:created_at)''',item)
        return self.evaluation_cases(project_id)[0]

    def evaluation_cases(self,project_id,active_only=False):
        query='SELECT * FROM evaluation_cases WHERE project_id=?'
        if active_only:
            query+=' AND active=1'
        query+=' ORDER BY created_at DESC,rowid DESC'
        rows=self._all(query,(project_id,))
        for row in rows:
            row['relevant_document_ids']=json.loads(row['relevant_document_ids'])
            row['expect_abstention']=bool(row['expect_abstention'])
            row['active']=bool(row['active'])
        return rows

    def set_evaluation_case_active(self,case_id,active):
        with self.lock,self.db:
            row=self._all('SELECT * FROM evaluation_cases WHERE id=?',(case_id,))
            if not row:
                raise LookupError('Caso de evaluación no encontrado.')
            self.db.execute('UPDATE evaluation_cases SET active=? WHERE id=?',
                            (int(bool(active)),case_id))
        return next(item for item in self.evaluation_cases(row[0]['project_id'])
                    if item['id']==case_id)

    def evaluation_chunks(self,project_id):
        return self._all('''SELECT c.id,c.document_id,c.page,c.content,d.filename
                            FROM chunks c JOIN documents d ON d.id=c.document_id
                            WHERE c.project_id=? ORDER BY c.rowid ASC''',(project_id,))

    def missing_evaluation_vectors(self,project_id,embedding_model,model_digest):
        return self._all('''SELECT c.id,c.content FROM chunks c
            LEFT JOIN evaluation_vectors v ON c.id=v.chunk_id
                AND v.embedding_model=? AND v.model_digest=?
            WHERE c.project_id=? AND v.chunk_id IS NULL ORDER BY c.rowid''',
            (embedding_model,model_digest,project_id))

    def insert_evaluation_vectors(self,embedding_model,model_digest,ids,vectors):
        if len(ids)!=len(vectors):
            raise ValueError('Faltan vectores de evaluación.')
        with self.lock,self.db:
            self.db.executemany('''INSERT OR REPLACE INTO evaluation_vectors
                (chunk_id,embedding_model,model_digest,embedding_json) VALUES (?,?,?,?)''',
                [(chunk_id,embedding_model,model_digest,json.dumps(vector))
                 for chunk_id,vector in zip(ids,vectors)])

    def evaluation_search(self,project_id,embedding_model,model_digest,vector,k):
        """Ranking por documento; evita sobrecontar múltiples chunks del mismo artículo."""
        rows=self._all('''SELECT c.id,c.document_id,c.page,c.content,d.filename,
                            v.embedding_json FROM chunks c
                            JOIN evaluation_vectors v ON c.id=v.chunk_id
                            JOIN documents d ON d.id=c.document_id
            WHERE c.project_id=? AND v.embedding_model=? AND v.model_digest=?''',
                       (project_id,embedding_model,model_digest))
        ranking=[]
        for row in rows:
            score=cosine(vector,json.loads(row.pop('embedding_json')))
            if score>-1.0:
                row['similitud']=score
                ranking.append(row)
        seen=set()
        distinct=[]
        for row in sorted(ranking,key=lambda r:r['similitud'],reverse=True):
            if row['document_id'] in seen:
                continue
            seen.add(row['document_id'])
            distinct.append(row)
            if len(distinct)>=k:
                break
        return distinct

    def create_evaluation_run(self,project_id,config,cases):
        item={'id':str(uuid.uuid4()),'project_id':project_id,'status':'en_cola',
              'corpus_fingerprint':self.fingerprint(project_id),
              'config_json':json.dumps(config,ensure_ascii=False,sort_keys=True),
              'cases_snapshot_json':json.dumps(cases,ensure_ascii=False,sort_keys=True),
              'completed_tasks':0,
              'total_tasks':len(cases)*len(config['llm_models'])*len(config['embedding_models']),
              'summary_json':'{}','error_message':'','created_at':now_iso(),
              'started_at':None,'finished_at':None}
        with self.lock,self.db:
            self.db.execute('''INSERT INTO evaluation_runs
                (id,project_id,status,corpus_fingerprint,config_json,cases_snapshot_json,
                 completed_tasks,total_tasks,summary_json,error_message,
                 created_at,started_at,finished_at)
                 VALUES (:id,:project_id,:status,:corpus_fingerprint,:config_json,
                 :cases_snapshot_json,:completed_tasks,:total_tasks,:summary_json,
                 :error_message,:created_at,:started_at,:finished_at)''',item)
        return self.evaluation_run(item['id'])

    def update_evaluation_run(self,run_id,status=None,completed_tasks=None,
                              summary=None,error_message=None):
        updates=[]
        params=[]
        for name,value in [('status',status),('completed_tasks',completed_tasks),
                           ('summary_json',json.dumps(summary,ensure_ascii=False) if summary is not None else None),
                           ('error_message',error_message)]:
            if value is not None:
                updates.append(f'{name}=?')
                params.append(value)
        if status=='ejecutando':
            updates.append('started_at=?')
            params.append(now_iso())
        if status in {'completada','completada_con_errores','fallida','interrumpida'}:
            updates.append('finished_at=?')
            params.append(now_iso())
        if updates:
            with self.lock,self.db:
                self.db.execute('UPDATE evaluation_runs SET '+','.join(updates)+' WHERE id=?',
                                (*params,run_id))
        return self.evaluation_run(run_id)

    def add_evaluation_result(self,run_id,case_id,llm_model,embedding_model,
                              metrics,answer,sources,error_message,duration_ms):
        with self.lock,self.db:
            self.db.execute('''INSERT INTO evaluation_results
                (id,run_id,case_id,llm_model,embedding_model,metrics_json,answer_text,
                 sources_json,error_message,duration_ms) VALUES (?,?,?,?,?,?,?,?,?,?)''',
                (str(uuid.uuid4()),run_id,case_id,llm_model,embedding_model,
                 json.dumps(metrics),answer,json.dumps(sources,ensure_ascii=False),
                 error_message,duration_ms))

    def evaluation_results(self,run_id):
        rows=self._all('''SELECT * FROM evaluation_results WHERE run_id=?
                          ORDER BY rowid ASC''',(run_id,))
        for row in rows:
            row['metricas']=json.loads(row.pop('metrics_json'))
            row['fuentes']=json.loads(row.pop('sources_json'))
        return rows

    def evaluation_run(self,run_id,with_results=False):
        rows=self._all('SELECT * FROM evaluation_runs WHERE id=?',(run_id,))
        if not rows:
            return None
        item=rows[0]
        item['configuracion']=json.loads(item.pop('config_json'))
        item['casos_congelados']=json.loads(item.pop('cases_snapshot_json'))
        item['resumen']=json.loads(item.pop('summary_json'))
        if with_results:
            item['resultados']=self.evaluation_results(run_id)
        return item

    def evaluation_runs(self,project_id):
        rows=self._all('''SELECT id FROM evaluation_runs WHERE project_id=?
                          ORDER BY created_at DESC,rowid DESC''',(project_id,))
        return [self.evaluation_run(row['id']) for row in rows]

