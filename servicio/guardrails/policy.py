"""Guardrails conservadores; registrar falsos positivos durante la evaluación."""

import json
import re


class GuardrailRejected(ValueError):
    pass


def format_structured_comparison(raw,sources,requested_groups,question):
    """Convierte referencias expresamente declaradas en JSON a texto verificable.

    No crea referencias: cada etiqueta procede del campo fuentes del modelo.
    """
    try:
        decoded=json.loads(raw.strip())
        items=decoded['afirmaciones']
        conclusion=decoded['conclusion']
    except (TypeError,ValueError,KeyError,AttributeError):
        raise GuardrailRejected('La comparación no tiene el JSON de evidencia requerido.')
    if not isinstance(items,list) or not 1<=len(items)<=4 or not isinstance(conclusion,dict):
        raise GuardrailRejected('Estructura de afirmaciones comparativas inválida.')
    accepted={item['ref'] for item in sources}
    lines=[]
    for item in [*items,conclusion]:
        if not isinstance(item,dict):
            raise GuardrailRejected('Una afirmación comparativa no es un objeto válido.')
        message=item.get('texto')
        refs=item.get('fuentes')
        if (not isinstance(message,str) or not message.strip() or
                not isinstance(refs,list) or not refs or
                any(not isinstance(ref,str) or ref not in accepted for ref in refs)):
            raise GuardrailRejected('Afirmación estructurada sin referencias válidas.')
        sentence=re.sub(r'(?:\s*\[F\d+\])+\s*[.!?]?\s*$','',message.strip()).strip()
        lines.append(sentence+' '+ ' '.join(dict.fromkeys(refs)))
    answer='\n'.join(lines)
    check_comparative_reasoning(answer,sources,requested_groups,question)
    return answer


def normalize_citation_labels(answer,sources):
    """Normaliza solo variantes tipográficas inequívocas de referencias existentes.

    No agrega fuentes ni altera el contenido científico: [f 1] equivale a
    [F1], pero una referencia desconocida sigue siendo rechazada.
    """
    if not isinstance(answer,str):
        return answer
    accepted={source['ref'].upper():source['ref'] for source in sources}

    def replacement(match):
        key=f'[F{int(match.group(1))}]'
        return accepted.get(key,key)

    answer=re.sub(
        r'\[\s*[Ff]\s*\d+(?:\s*[,;]\s*[Ff]\s*\d+)+\s*\]',
        lambda m:' '.join(re.findall(r'\[F\d+\]',re.sub(
            r'[Ff]\s*(\d+)',lambda x:f'[F{x.group(1)}]',m.group()))),
        answer)
    answer=re.sub(r'[【(]\s*[Ff]\s*(\d+)\s*[】)]',
                  lambda m:f'[F{m.group(1)}]',answer)
    return re.sub(r'\[\s*[Ff]\s*(\d+)\s*\]',replacement,answer)


def keep_cited_comparison_sentences(answer):
    """Retiene afirmaciones atribuidas, descartando solo prefacios sin citas.

    Nunca inventa etiquetas ni adjunta citas a texto que llegó sin fuente.
    Las afirmaciones conservadas deben pasar después todos los guardrails.
    """
    if not isinstance(answer,str):
        return answer
    lines=[]
    for paragraph in answer.splitlines():
        for sentence in re.split(
                r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚ¿])',paragraph.strip()):
            cleaned=sentence.strip()
            cleaned=re.sub(r'^\s*(?:[-*]|\d+[.)])\s*','',cleaned)
            if re.search(r'(?:\[F\d+\]\s*)+[.!?]?\s*$',cleaned):
                lines.append(cleaned)
    return '\n'.join(lines) if len(lines)>=2 else answer


def check_input(question):
    # Regla 1: estructura, longitud y caracteres de control.
    if not isinstance(question,str) or not 8<=len(question.strip())<=1200:
        raise GuardrailRejected('La solicitud debe contener entre 8 y 1200 caracteres.')
    if any(ord(c)<32 and c not in '\n\t\r' for c in question):
        raise GuardrailRejected('La solicitud contiene caracteres de control no permitidos.')
    # Regla 2: patrones explícitos para desviar la jerarquía de instrucciones.
    patterns=[r'ignora (todas )?(las )?instrucciones',
              r'ignore (all )?(previous|system) instructions',
              r'(revela|muestra|imprime) (el )?(prompt|mensaje) (del )?sistema',
              r'\b(system|developer) prompt\b']
    if any(re.search(p,question,re.IGNORECASE) for p in patterns):
        raise GuardrailRejected('Solicitud bloqueada: posible intento de alterar las instrucciones del sistema.')


def check_text_output(answer,sources):
    # Salida 1: formato y valor real.
    if not isinstance(answer,str) or not answer.strip():
        raise GuardrailRejected('El modelo no produjo texto válido.')
    # Salida 2: al menos una cita a uno de los fragmentos recuperados.
    labels=set(re.findall(r'\[F\d+\]',answer))
    accepted={source['ref'] for source in sources}
    if not labels or not labels.issubset(accepted):
        raise GuardrailRejected('La respuesta no contiene citas válidas del contexto recuperado.')
    # Una bibliografía final no justifica por sí sola las afirmaciones previas.
    body=re.split(r'(?im)^\s*(?:referencias|fuentes|bibliograf[ií]a)\s*:',answer,maxsplit=1)[0]
    if not re.search(r'\[F\d+\]',body):
        raise GuardrailRejected('Las citas deben aparecer en las afirmaciones, no solo en referencias finales.')
    paragraphs=[part.strip() for part in re.split(r'\n\s*\n',body) if part.strip()]
    for paragraph in paragraphs:
        if len(paragraph)>=90 and not re.search(r'\[F\d+\]',paragraph):
            raise GuardrailRejected('Existe un párrafo científico extenso sin cita documental.')


def check_quantitative_support(answer,sources):
    """Comprueba que cifras con magnitud citadas existan en sus pasajes.

    Es un filtro conservador de consistencia numérica, no un verificador de
    inferencia semántica ni una aprobación científica del resultado.
    """
    by_ref={source['ref']:source['fragmento'] for source in sources}
    numeric_pattern=re.compile(
        r'(\d+(?:[.,]\d+)?)\s*(%|J\s*/\s*mm\s*(?:3|³)|HV|[µμ]m)',re.I)

    def normalized(item):
        value=item.group(1).replace(',','.')
        unit=item.group(2).lower().replace(' ','').replace('³','3').replace('μ','µ')
        return value,unit

    for line in answer.splitlines():
        measures=[normalized(m) for m in numeric_pattern.finditer(line)]
        if not measures:
            continue
        cited=set(re.findall(r'\[F\d+\]',line))
        if not cited:
            # Las cifras no pueden quedar avaladas solo por una cita en otra línea.
            raise GuardrailRejected('Existe una magnitud numérica sin cita en la misma línea.')
        reported=set()
        for ref in cited:
            reported.update(normalized(m) for m in numeric_pattern.finditer(
                by_ref.get(ref,'')))
        if any(measure not in reported for measure in measures):
            raise GuardrailRejected(
                'Una magnitud numérica no aparece con ese valor y unidad en las fuentes citadas.')


def check_comparative_reasoning(answer,sources,requested_groups,question):
    """Comprueba estructura de razonamiento y cobertura de citas por publicación.

    No certifica equivalencia física: verifica que el texto comparativo esté
    fundamentado, contraste resultados y cite todos los grupos solicitados.
    """
    check_text_output(answer,sources)
    check_quantitative_support(answer,sources)
    lines=[re.sub(r'^\s*(?:[-*]|\d+[.)])\s*','',line).strip()
           for line in answer.splitlines() if line.strip()]
    if len(lines)<2 or len(lines)>6:
        raise GuardrailRejected(
            'La comparación necesita entre dos y seis afirmaciones verificables.')
    for line in lines:
        if not re.search(r'(?:\[F\d+\]\s*)+[.!?]?\s*$',line):
            raise GuardrailRejected(
                'Cada afirmación comparativa debe terminar con una cita de su evidencia.')
    by_ref={source['ref']:source['documento_id'] for source in sources}
    used={by_ref[ref] for ref in re.findall(r'\[F\d+\]',answer)
          if ref in by_ref}
    missing=[name for name,ids in requested_groups.items()
             if not used.intersection(ids)]
    if missing:
        raise GuardrailRejected(
            'La respuesta omite citas de publicaciones solicitadas: '
            +', '.join(missing)+'.')
    if len(set(by_ref.values()))>=2 and len(used)<2:
        raise GuardrailRejected(
            'La comparación cita un solo estudio; se requieren al menos dos.')
    if len(requested_groups)>=2 and re.search(
            r'\bequival|\bgarantiz',question,re.I):
        conclusion_refs=set(re.findall(r'\[F\d+\]',lines[-1]))
        conclusion_documents={by_ref[ref] for ref in conclusion_refs if ref in by_ref}
        if any(not conclusion_documents.intersection(ids)
               for ids in requested_groups.values()):
            raise GuardrailRejected(
                'La conclusión debe citar ambas publicaciones comparadas.')
    if not re.search(
            r'\baunque\b|\bsin embargo\b|\bmientras\b|'
            r'\bpor (?:ello|tanto|consiguiente)\b|\bno (?:se puede|es posible|'
            r'necesariamente|equivale|garantiz|demuestra|implica|permite)\b|'
            r'\bno puede\b|\bdifier|\bdiferenc|\bcontraste\b',
            answer,re.I):
        raise GuardrailRejected(
            'La respuesta enumera fuentes, pero no justifica la comparación.')
    if re.search(r'\bequival|\bgarantiz',question,re.I) and re.search(
            r'(?im)^\s*(?:s[ií][,:]?\s+)?(?:es equivalente|'
            r'garantiza|se garantiza|queda garantizado)\b',answer):
        raise GuardrailRejected(
            'No se permite asegurar equivalencia universal entre estudios.')


def _relevant_excerpt(fragment,question):
    """Cita un tramo original cercano a resultados, no solo el inicio del PDF."""
    raw=' '.join(fragment.split())
    if len(raw)<=900:
        return raw
    if not re.search(r'energ[ií]a|energy|\bved\b',question,re.I):
        return raw[:900]+'…'
    anchors=list(re.finditer(
        r'relative\s+densit(?:y|ies)|densidad\s+relativa|'
        r'density\s+(?:greater|higher|above|over)|\b\d+(?:[.,]\d+)?\s*%',
        raw,re.I))
    if not anchors:
        return raw[:900]+'…'

    def score(anchor):
        left=max(0,anchor.start()-500)
        right=min(len(raw),anchor.start()+400)
        window=raw[left:right]
        return (4*len(re.findall(r'\d+(?:[.,]\d+)?\s*J\s*/\s*mm\s*(?:3|³)',window,re.I))
                +3*len(re.findall(r'\d+(?:[.,]\d+)?\s*%',window))
                +2*bool(re.search(r'relative\s+densit|densidad\s+relativa',window,re.I)))

    best=max(anchors,key=score)
    start=max(0,best.start()-500)
    end=min(len(raw),start+900)
    return ('…' if start else '')+raw[start:end]+('…' if end<len(raw) else '')


def source_only_fallback(sources,question=''):
    """Muestra evidencia centrada en la consulta, sin sintetizar ni atribuir citas."""
    if not sources:
        raise GuardrailRejected('No hay fuentes para mostrar evidencia.')
    lines=[
        'La respuesta del modelo no incluyó referencias verificables, incluso después '
        'de un reintento. Para evitar atribuir conclusiones a fuentes incorrectas, '
        'se descartó esa respuesta.',
        '',
        'Fragmentos recuperados del corpus para revisión:',
        ''
    ]
    ranked=list(sources)
    if re.search(r'energ[ií]a|energy|\bved\b',question,re.I) and re.search(
            r'densidad|density',question,re.I):
        def evidence_score(source):
            fragment=source['fragmento']
            return (3*len(re.findall(r'\d+(?:[.,]\d+)?\s*J\s*/\s*mm\s*(?:3|³)',fragment,re.I))
                    +2*len(re.findall(r'\d+(?:[.,]\d+)?\s*%',fragment))
                    +3*bool(re.search(r'relative\s+densit|densidad\s+relativa',fragment,re.I)))
        ranked.sort(key=evidence_score,reverse=True)
        # Mostrar primero investigaciones distintas, si están disponibles.
        diverse=[]
        observed=set()
        for source in ranked:
            if source['documento'] not in observed:
                diverse.append(source)
                observed.add(source['documento'])
        ranked=diverse+[source for source in ranked if source not in diverse]
    seen=set()
    for source in ranked:
        key=(source['documento'],source['pagina'])
        if key in seen:
            continue
        seen.add(key)
        excerpt=_relevant_excerpt(source['fragmento'],question)
        lines.append(f"{source['ref']} {source['documento']}, página {source['pagina']}: «{excerpt}»")
        lines.append('')
        if len(seen)>=3:
            break
    lines.append('Este contenido no es una síntesis científica: verifica los pasajes en los documentos originales.')
    return '\n'.join(lines)


def correct_quantitative_omission(question,answer,sources):
    """Evita negar cifras verificables recuperadas sobre energía y densidad.

    Esta regla es deliberadamente estrecha: no interpreta tablas ni infiere
    resultados físicos. Cuando encuentra una contradicción clara, presenta el
    texto documental original para revisión humana en vez de inventar síntesis.
    """
    query=question.casefold()
    if not (re.search(r'energ[ií]a|energy|\bved\b',query)
            and re.search(r'densidad|density',query)):
        return None
    denial=re.search(
        r'\b(?:no se (?:reportan|proporcionan|presentan|incluyen|encuentran|mencionan)'
        r'|no hay|sin)\b[^.\n]{0,130}\b(?:datos|valores|resultados|cifras|informaci[oó]n)\b',
        answer,flags=re.IGNORECASE)
    if not denial:
        return None
    if re.search(r'\b(?:datos|valores|resultados|cifras)\s+'
                 r'(?:adicionales|extra|complementarios)\b',
                 answer[denial.start():denial.end()+24],flags=re.I):
        return None
    excerpts=[]
    for source in sources:
        raw=' '.join(source['fragmento'].split())
        lower=raw.casefold()
        if not (re.search(r'energy\s+density|densidad\s+(?:volum[eé]trica\s+)?de\s+energ[ií]a',lower)
                and re.search(r'relative\s+densit(?:y|ies)|density\s+'
                              r'(?:greater|higher|over|above|of|at least)'
                              r'|densidad(?:es)?\s+(?:relativa|mayor|superior)',lower)):
            continue
        energy=re.search(r'\b\d+(?:[.,]\d+)?\s*J\s*/\s*mm\s*(?:3|³)\b',raw,flags=re.I)
        percent=re.search(r'\b\d+(?:[.,]\d+)?\s*%',raw)
        if not energy or not percent or abs(energy.start()-percent.start())>420:
            continue
        start=max(0,min(energy.start(),percent.start())-180)
        end=min(len(raw),max(energy.end(),percent.end())+110)
        excerpt=('…' if start else '')+raw[start:end]+('…' if end<len(raw) else '')
        excerpts.append((source,excerpt))
        if len(excerpts)>=2:
            break

    if not excerpts:
        return None
    lines=[
        'Se detectó una contradicción: la respuesta del modelo negaba resultados '
        'cuantitativos que sí aparecen en los fragmentos recuperados. Se muestra '
        'la evidencia original, sin añadir interpretaciones automáticas:',
        ''
    ]
    for source,excerpt in excerpts:
        lines.append(f"{source['ref']} {source['documento']}, página {source['pagina']}: «{excerpt}»")
        lines.append('')
    lines.append('Revisa estos pasajes y sus figuras o tablas antes de formular una conclusión científica.')
    return '\n'.join(lines)


def check_map_output(items,sources):
    # Salida 1: estructura formal de registros y restricciones de tamaño.
    if not isinstance(items,list) or not 1<=len(items)<=12:
        raise GuardrailRejected('La extracción no tiene la estructura esperada de afirmaciones.')
    accepted={source['ref'] for source in sources}
    # Salida 2: cada afirmación enlaza fuentes recuperadas y existentes.
    for item in items:
        if not isinstance(item,dict) or not 10<=len(str(item.get('texto','')).strip())<=1000:
            raise GuardrailRejected('Existe una afirmación vacía o con formato inválido.')
        refs=item.get('fuentes')
        if not isinstance(refs,list) or not refs or any(ref not in accepted for ref in refs):
            raise GuardrailRejected('Existe una afirmación sin referencias verificables.')

