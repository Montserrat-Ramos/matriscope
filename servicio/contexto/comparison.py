"""Comparación documental trazable sin inferencias experimentales automáticas."""

import re

from servicio.contexto.evidence import extract_evidence,excerpt_for_evidence
from servicio.contexto.retrieval import is_comparison_question


PROPERTIES=(
    ('Energía volumétrica',r'energy\s+densit(?:y|ies)|volumetric\s+energy|'
                           r'volume\s+energy|\bVED\b|'
                           r'densidad\s+(?:volum[eé]trica\s+)?de\s+energ[ií]a'),
    ('Densidad relativa',r'relative\s+densit(?:y|ies)|densidad\s+relativa|'
                         r'density\s+(?:greater|higher|above|of\s+at\s+least)|'
                         r'maximum\s+densification'),
    ('Porosidad',r'porosity|porosidad|\bpores?\b'),
    ('Dureza',r'hardness|dureza'),
    ('Tamaño de poro',r'pore\s+size|tama[nñ]o\s+de\s+poro'),
    ('Rugosidad',r'roughness|rugosidad'),
    ('Potencia láser',r'laser\s+power|\bpower\s+(?:is|was|at|of|and|\d)|'
                       r'potencia\s+(?:de\s+)?l[aá]ser'),
    ('Velocidad de escaneo',r'scan(?:ning)?\s+speed|scan\s+velocity|'
                              r'velocidad\s+de\s+escaneo'),
    ('Distancia entre pasadas',r'hatch\s+spacing|distancia\s+entre\s+pasadas'),
)


def _variables(fragment,findings):
    # Evaluar el pasaje completo, no el recorte, y distinguir propiedades.
    result=[label for label,pattern in PROPERTIES if re.search(pattern,fragment,re.I)]
    if any(item['densidad']!='—' for item in findings) and 'Densidad relativa' not in result:
        result.append('Densidad relativa')
    return result


def build_document_comparison(question,sources):
    """Devuelve evidencia explícita por artículo y diferencias de reporte.

    El orden lo proporciona retrieval.select_contexts. Cada fila conserva
    documento y página; nunca junta energía de un PDF con % de otro.
    """
    if not is_comparison_question(question):
        return None
    selected=[]
    seen_documents=set()
    for source in sources:
        key=source.get('documento_id',source['documento'])
        if key in seen_documents:
            continue
        seen_documents.add(key)
        raw=source['fragmento']
        findings=extract_evidence(raw)
        excerpt=excerpt_for_evidence(raw,findings)
        safe_facts=[{k:v for k,v in fact.items() if not k.startswith('_')}
                    for fact in findings]
        selected.append({
            'ref':source['ref'],
            'documento':source['documento'],
            'pagina':source['pagina'],
            'doi':source.get('doi',''),
            'variables':_variables(raw,findings),
            'resultados':safe_facts,
            'fragmento':excerpt,
        })
        if len(selected)>=5:
            break
    if len(selected)<2:
        return {'suficiente':False,'filas':selected,
                'mensaje':('Se recuperó menos de dos artículos distintos. '
                           'No es posible comparar investigaciones con esta evidencia.')}

    common=set(selected[0]['variables'])
    for row in selected[1:]:
        common.intersection_update(row['variables'])
    shared=', '.join(sorted(common)) if common else 'ninguna identificada en todos los pasajes'

    direct=[]
    range_refs=[]
    threshold_refs=[]
    non_numeric=[]
    methods=[]
    porosity_refs=[]
    qualitative_refs=[]
    for row in selected:
        related=[fact for fact in row['resultados']
                 if fact['energia']!='—' and fact['densidad']!='—']
        if related:
            direct.append(row['ref'])
        else:
            non_numeric.append(row['ref'])
        if any(fact['tipo']=='intervalo reportado' for fact in row['resultados']):
            range_refs.append(row['ref'])
        if any(fact['tipo']=='umbral reportado' for fact in row['resultados']):
            threshold_refs.append(row['ref'])
        if any(fact['metodo']!='No especificado en el pasaje'
               for fact in row['resultados']):
            methods.append(row['ref'])
        if any(fact['porosidad']!='—' for fact in row['resultados']):
            porosity_refs.append(row['ref'])
        if any(fact['tipo']=='diferencia cualitativa entre métodos'
               for fact in row['resultados']):
            qualitative_refs.append(row['ref'])

    details=[]
    if range_refs:
        details.append('intervalos de energía en '+', '.join(range_refs))
    if threshold_refs:
        details.append('umbrales de energía en '+', '.join(threshold_refs))
    if methods:
        details.append('métodos de medición explícitos en '+', '.join(methods))
    if porosity_refs:
        details.append('valores de porosidad en '+', '.join(porosity_refs))
    if qualitative_refs:
        details.append('diferencias cualitativas entre métodos en '+', '.join(qualitative_refs))
    descriptions='; '.join(details) if details else 'sin relaciones cuantitativas comparables en los pasajes elegidos'
    message=(f'Se recuperaron pasajes de {len(selected)} artículos distintos. '
             f'Coincidencia temática en los pasajes: {shared}. '
             f'Asociaciones explícitas de energía y densidad relativa: '
             f'{len(direct)} artículo(s) ({", ".join(direct) if direct else "ninguno"}). '
             f'Diferencias en el tipo de evidencia: {descriptions}. '
             + (f'En {", ".join(non_numeric)} no se identificó un par '
                'energía-densidad relativa explícito en el fragmento elegido. '
                if non_numeric else '')
             + 'Estas son diferencias de reporte, NO diferencias de comportamiento '
             'físico demostradas. No se equiparan métodos, máquinas, muestras '
             'ni porcentajes de estudios distintos sin comprobar sus condiciones.')
    if re.search(r'\bequival|\bgarantiz',question,re.I):
        message=('No puede establecerse que una recomendación de un estudio '
                 'garantice los resultados de otro a partir de estos pasajes. '
                 +message)
    return {'suficiente':True,'filas':selected,'mensaje':message}
