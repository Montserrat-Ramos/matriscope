"""Reordenación de pasajes para preguntas cuantitativas, sin crear hallazgos."""

import re


def is_numeric_table_fragment(content):
    """Detecta tablas/series numéricas OCR sin suficiente prosa traducible."""
    numbers=re.findall(r'(?<![\w])[+\-−]?\d+(?:[.,]\d+)?',content)
    words=re.findall(r'[A-Za-zÀ-ÿ]{3,}',content)
    return len(content)>220 and len(numbers)>=35 and len(numbers)>.8*len(words)


def is_comparison_question(question):
    return bool(re.search(
        r'\bcompar(?:a|ar|aci[oó]n|aciones|ando|en|emos)\b|'
        r'\bdiferencias?\b|\bcoincidencias?\b|\bcontrasta(?:r)?\b|'
        r'\bcompar(?:e|ison|ing)\b|\bversus\b|'
        r'\bequival(?:e|en|er|encia|ente|entes)\b|'
        r'\bgarantiz(?:a|an|ar|ada|ado)\b',question,re.I))


def requested_document_groups(question,documents):
    """Detecta referencias a documentos indexados por nombre de archivo.

    La agrupación por prefijo permite «JMMP» y «Metals» sin fijar una lista
    de revistas. Si hay varios Metals, la evidencia numérica elige pasajes;
    nunca se declara que el nombre por sí solo identifique un artículo único.
    """
    query=question.casefold()
    families={}
    precise={}
    for doc in documents:
        filename=str(doc.get('filename','')).casefold()
        stem=re.sub(r'\.[a-z0-9]+$','',filename)
        family=re.split(r'[-_\s.]',stem,1)[0]
        if len(family)<4 or not family.isalpha() or family in {
                'paper','fuente','document','documento','article','articulo'}:
            continue
        if len(stem)>len(family)+2 and stem in query:
            precise.setdefault(stem,set()).add(doc['id'])
            families[family]=None
        elif re.search(r'(?<!\w)'+re.escape(family)+r'(?!\w)',query):
            families.setdefault(family,set())
            if families[family] is not None:
                families[family].add(doc['id'])
    return {**{name:ids for name,ids in families.items() if ids},**precise}


def is_energy_density_question(question):
    text=question.casefold()
    return (bool(re.search(r'energ[ií]a|energy|\bved\b',text))
            and bool(re.search(r'densidad|density',text)))


def select_contexts(question,candidates,limit,requested_groups=None):
    """Da prioridad a pasajes con ambas magnitudes explícitas.

    Conserva el umbral de similitud de la búsqueda original. No transforma los
    resultados ni mezcla valores de diferentes fuentes. Para otras consultas,
    mantiene estrictamente el orden vectorial original.
    """
    if is_comparison_question(question):
        # Para comparaciones priorizar resultados medidos SOBRE introducciones
        # y después diversificar: cinco fragmentos no son cinco estudios.
        from servicio.contexto.evidence import evidence_relevance
        q=question.casefold()
        concepts=[(r'porosidad|porosity|pores?',0.15),
                  (r'densidad|density|densification',0.15),
                  (r'energ[ií]a|energy|\bved\b',0.08),
                  (r'dureza|hardness',0.12)]
        active=[(pattern,bonus) for pattern,bonus in concepts
                if re.search(pattern,q,re.I)]
        requested_numbers={value.replace(',','.') for value in re.findall(
            r'(?<!\w)\d+(?:[.,]\d+)?',question)}

        def score(item):
            content=item['content']
            reported_numbers={value.replace(',','.') for value in re.findall(
                r'(?<!\w)\d+(?:[.,]\d+)?',content)}
            # Una tabla de composición elemental puede preceder a un pasaje
            # de densificación en el mismo fragmento. Sus muchas cifras no
            # lo convierten en el mejor extracto para comparar porosidad.
            table_noise=(0.9 if re.search(
                r'Table\s+\d+\.\s+Chemical\s+composition',content,re.I)
                and not re.search(r'composici[oó]n|composition',q,re.I)
                else 0.0)
            return (float(item['similarity'])+
                    evidence_relevance(content,question)+
                    .45*len(requested_numbers & reported_numbers)+
                    sum(bonus for pattern,bonus in active
                        if re.search(pattern,content,re.I))-
                    table_noise)

        ordered=sorted(candidates,key=score,reverse=True)
        # Cuando el usuario nombra dos publicaciones, reservar una fuente
        # de cada una antes de completar los lugares restantes. No mezclar
        # pasajes de otras revistas para simular una comparación.
        if requested_groups and len(requested_groups)>=2:
            from servicio.contexto.evidence import extract_evidence
            if not re.search(r'\btablas?\b|\btables?\b|\bfiguras?\b|\bfigures?\b',q):
                readable=[row for row in ordered
                          if not is_numeric_table_fragment(row['content'])]
                if all(any(row['document_id'] in ids for row in readable)
                       for ids in requested_groups.values()):
                    ordered=readable
            selected=[]
            chosen_ids=set()
            chosen_documents=set()
            for group_ids in requested_groups.values():
                match=next((row for row in ordered
                            if row['document_id'] in group_ids),None)
                if match is not None and match['id'] not in chosen_ids:
                    selected.append(match)
                    chosen_ids.add(match['id'])
                    chosen_documents.add(match['document_id'])
            # Una pregunta puntual de equivalencia debe comparar primero
            # los dos resultados relevantes, no enviar cinco páginas a Qwen.
            if (re.search(r'\bequival|\bgarantiz',q) and
                    len(selected)==len(requested_groups) and
                    all(extract_evidence(item['content']) for item in selected)):
                return selected[:limit]
            def repeated_result(row):
                facts=extract_evidence(row['content'])
                facts={tuple(fact.get(key) for key in
                             ('tipo','energia','densidad','porosidad','metodo'))
                       for fact in facts}
                if not facts:
                    return False
                for existing in selected:
                    if existing['document_id']!=row['document_id']:
                        continue
                    prior={tuple(fact.get(key) for key in
                                 ('tipo','energia','densidad','porosidad','metodo'))
                           for fact in extract_evidence(existing['content'])}
                    if facts.issubset(prior):
                        return True
                return False
            for row in ordered:
                if len(selected)>=limit:break
                if (row['document_id'] in chosen_documents
                        and row['id'] not in chosen_ids
                        and (row['document_id'],row['page']) not in {
                            (item['document_id'],item['page']) for item in selected}
                        and not repeated_result(row)):
                    selected.append(row)
                    chosen_ids.add(row['id'])
            return selected[:limit]
        selected=[]
        documents=set()
        for item in ordered:
            if item['document_id'] not in documents:
                selected.append(item)
                documents.add(item['document_id'])
            if len(selected)>=limit:
                return selected
        seen_ids={item['id'] for item in selected}
        selected.extend(item for item in ordered if item['id'] not in seen_ids)
        return selected[:limit]

    from servicio.contexto.porosity import is_energy_porosity_question
    if is_energy_porosity_question(question):
        # Para una pregunta sobre POROSIDAD, los pasajes que explican el
        # mecanismo de los defectos son más útiles que un mero porcentaje
        # de densidad relativa. Conservar variedad de artículos.
        def porosity_score(item):
            content=item['content']
            both=bool(re.search(r'porosidad|porosity',content,re.I) and
                      re.search(r'energy|energ[ií]a|\bVED\b',content,re.I))
            mechanism=bool(re.search(r'lack.of.fusion|keyhole|'
                                     r'higher the energy density|lower the porosity',
                                     content,re.I))
            return float(item['similarity']) + (0.3 if both else 0) + (0.35 if mechanism else 0)

        ranked=sorted(candidates,key=porosity_score,reverse=True)
        chosen=[]
        documents=set()
        for item in ranked:
            if item['document_id'] not in documents:
                chosen.append(item)
                documents.add(item['document_id'])
                if len(chosen)>=limit:
                    return chosen
        chosen_ids={item['id'] for item in chosen}
        chosen.extend(item for item in ranked if item['id'] not in chosen_ids)
        return chosen[:limit]

    if not is_energy_density_question(question):
        return candidates[:limit]

    energy_value=re.compile(r'\b\d+(?:[.,]\d+)?\s*J\s*/\s*mm\s*(?:3|³)\b',re.I)
    percent_value=re.compile(r'\b\d+(?:[.,]\d+)?\s*%',re.I)
    density_measure=re.compile(
        r'relative\s+densit(?:y|ies)|density\s+(?:greater|higher|over|above|of|at least)'
        r'|densidad(?:es)?\s+(?:relativa|mayor|superior)',re.I)

    # Una pregunta que especifica 99.9 % no debe perder el pasaje con esa
    # magnitud ante otro intervalo con 99.8 %, aunque el segundo sea muy similar.
    target_percent=None
    if re.search(r'densidad(?:es)?\s+relativa|relative\s+densit',question,re.I):
        requested=re.findall(r'(\d+(?:[.,]\d+)?)\s*%',question)
        if len(requested)==1:
            target_percent=requested[0].replace(',','.')

    def score(item):
        content=' '.join(item['content'].split())
        value=float(item['similarity'])
        has_density=bool(density_measure.search(content))
        energy=list(energy_value.finditer(content))
        percents=list(percent_value.finditer(content))
        if has_density:
            value+=0.12
        if energy:
            value+=0.06
        if has_density and any(abs(e.start()-p.start())<=520
                               for e in energy for p in percents):
            value+=0.55
        if target_percent is not None and energy:
            for percent in percents:
                number=percent.group().split('%')[0].strip().replace(',','.')
                if number!=target_percent:
                    continue
                nearby=content[max(0,percent.start()-250):percent.end()+100]
                if density_measure.search(nearby) and any(
                        abs(e.start()-percent.start())<=520 for e in energy):
                    value+=0.85
                    break
        return value

    ranked=sorted(candidates,key=score,reverse=True)
    result=[]
    seen_pages=set()
    for item in ranked:
        key=(item['document_id'],item['page'])
        if key in seen_pages:
            continue
        seen_pages.add(key)
        result.append(item)
        if len(result)>=limit:
            return result
    # Corpus pequeños: permitir varios fragmentos de una misma página solo
    # cuando ya no queden páginas distintas.
    selected_ids={item['id'] for item in result}
    result.extend(item for item in ranked if item['id'] not in selected_ids)
    return result[:limit]
