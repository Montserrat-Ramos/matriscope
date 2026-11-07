import time
import uuid

from servicio.datos.sqlite_store import now_iso


class Trace:
    def __init__(self,store,project_id,function_name):
        self.store=store
        self.started=time.perf_counter()
        self.record={'id':str(uuid.uuid4()),'project_id':project_id,'status':'pendiente',
                     'function_name':function_name,'model':None,'cache':'ninguna',
                     'guardrail':'no_aplicado','iterations':0,'duration_ms':0,'created_at':now_iso()}

    @property
    def id(self):
        return self.record['id']

    def finish(self,status,**details):
        self.record.update(details)
        self.record['status']=status
        self.record['duration_ms']=int((time.perf_counter()-self.started)*1000)
        self.store.record_trace(self.record)
        return self.record


def metrics(store):
    rows=store.traces()
    latencies=[r['duration_ms'] for r in rows]
    return {
      'consultas_registradas':len(rows),
      'latencia_promedio_ms':round(sum(latencies)/len(latencies),1) if rows else None,
      'latencia_maxima_ms':max(latencies) if rows else None,
      'aciertos_cache_exacta':sum(r['cache']=='exacta' for r in rows),
      'aciertos_cache_semantica':sum(r['cache']=='semantica' for r in rows),
      'bloqueos_guardrails':sum(r['status']=='bloqueada' for r in rows),
      'uso_por_modelo':{name:sum(r['model']==name for r in rows) for name in sorted(set(r['model'] for r in rows if r['model']))},
      'retroalimentacion':store.feedback_count(),
      'trazas_recientes':rows[:20],
      'nota':'Las métricas se calculan de solicitudes reales registradas; no se incluyen datos de ejemplo.'
    }

