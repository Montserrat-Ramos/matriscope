"""Exportación auditable de cada ejecución, sin resultados inferidos."""

import csv
from io import StringIO


def safe_cell(value):
    """Neutraliza fórmulas al abrir archivos CSV en hojas de cálculo."""
    text='' if value is None else str(value)
    if text.lstrip().startswith(('=','+','-','@')) or text[:1] in {'\t','\r','\n'}:
        return "'"+text
    return text


def export_evaluation_csv(run):
    if run['status'] not in {'completada','completada_con_errores'}:
        raise ValueError('Solo se exportan ejecuciones finalizadas.')
    by_id={case['id']:case for case in run['casos_congelados']}
    output=StringIO(newline='')
    writer=csv.writer(output,quoting=csv.QUOTE_ALL)
    writer.writerow(['ejecucion_id','estado_ejecucion','huella_corpus','caso_id','pregunta',
        'documentos_pertinentes','sin_evidencia','llm','llm_digest','embeddings',
        'embeddings_digest','top_k','documentos_recuperados','precision_at_k',
        'recall_at_k','mrr','hit_at_k','abstencion_declarada',
        'integridad_formal_citas','latencia_ms','respuesta','error'])
    config=run['configuracion']
    for result in run['resultados']:
        case=by_id.get(result['case_id'],{})
        metric=result['metricas']
        values=[run['id'],run['status'],run['corpus_fingerprint'],result['case_id'],
            case.get('question',''),'; '.join(case.get('relevant_document_ids',[])),
            case.get('expect_abstention',False),result['llm_model'],
            config.get('model_digests',{}).get(result['llm_model'],''),
            result['embedding_model'],config.get('model_digests',{}).get(result['embedding_model'],''),
            config['top_k'],'; '.join(src['documento_id'] for src in result['fuentes']),
            metric.get('precision_at_k'),metric.get('recall_at_k'),metric.get('mrr'),
            metric.get('hit_at_k'),metric.get('abstencion_declarada'),
            metric.get('integridad_formal_citas'),result['duration_ms'],
            result['answer_text'],result['error_message']]
        writer.writerow([safe_cell(value) for value in values])
    return output.getvalue().encode('utf-8-sig')
