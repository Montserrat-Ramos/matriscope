"""Relaciones experimentales explícitas para comparación documental.

Las reglas identifican estructuras textuales delimitadas. No estiman cifras,
no asocian magnitudes de documentos distintos y no sustituyen una lectura
metodológica de los artículos originales.
"""

import re

from servicio.contexto.quantitative import (PAIR,RANGE_BETWEEN,RANGE_FROM,SINGLE)


NUMBER=r'\d+(?:[.,]\d+)?'
UNIT=r'J\s*/\s*mm\s*(?:3|³)'

POROSITY_ENERGY=re.compile(
    rf'energy\s+density\s+of\s+(?P<energy>{NUMBER})\s*{UNIT}'
    rf'[^.!?]{{0,125}}?\bporosity\s+at\s+(?P<porosity>{NUMBER})\s*%',re.I)
ARCHIMEDES=re.compile(
    rf'maximum\s+densification\s+reached\s+was\s+(?P<arch>{NUMBER})\s*%'
    rf'.{{0,110}}?Archimedes.{{0,85}}?\b(?P<image>{NUMBER})\s*%'
    rf'\s+by\s+image\s+correlation',re.I|re.S)
OPTICAL_XCT_POROSITY=re.compile(
    rf'(?:measured|reported|predicted)\s+porosit(?:y|ies)'
    rf'.{{0,150}}?\boptical\b\s+and\s+\b(?:XCT|X-ray\s+(?:computed\s+)?tomography)\b'
    rf'.{{0,120}}?\b(?P<optical>{NUMBER})\s*%\s+and\s+'
    rf'(?P<xct>{NUMBER})\s*%\s*,?\s*respectively',re.I|re.S)
METHOD_CONTRAST=re.compile(
    r'XCT\s+measured\s+higher\s+porosity\s+at\s+low\s+power'
    r'.{0,175}?optical\s+microscopy\s+measured\s+higher\s+porosity'
    r'\s+at\s+high\s+power',re.I|re.S)
PORE_SIZE_RANGE=re.compile(
    rf'(?:average\s+)?pore\s+size\s+ranged\s+from\s+'
    rf'(?P<low>{NUMBER})\s*[µμ]m\s+to\s+(?P<high>{NUMBER})\s*[µμ]m'
    rf'(?:\s+when\s+(?:the\s+)?energy\s+density\s+was\s+'
    rf'(?P<condition>lower|higher)\s+than\s+(?P<energy>{NUMBER})\s*{UNIT})?',re.I)
HARDNESS_RANGE=re.compile(
    rf'(?:hardness\s+(?:in|at)\s+(?:the\s+)?energy\s+density\s+range\s+of\s+)'
    rf'(?P<energy>{NUMBER})\s*{UNIT}\s+or\s+higher'
    rf'.{{0,110}}?ranged\s+from\s+(?P<low>{NUMBER})\s*HV\s+to\s+'
    rf'(?P<high>{NUMBER})\s*HV',re.I|re.S)
ROUGHNESS_VALUE=re.compile(
    rf'\b(?P<metric>Ra|Rz)\s*(?:=|:|was|of)\s*'
    rf'(?P<value>{NUMBER})\s*[µμ]m\b',re.I)
POROSITY_SINGLE=re.compile(
    rf'\b(?:sectional\s+)?porosity\s+(?:was|of|at|reached|is)\s+'
    rf'(?P<value>{NUMBER})\s*%',re.I)
ENERGY_RECOMMENDATION=re.compile(
    rf'(?:volumetric\s+energy\s*\(\s*|energy\s+density\s+of\s+)'
    rf'(?P<energy>{NUMBER})\s*{UNIT}\s*\)?'
    rf'[^.!?]{{0,115}}?(?:must\s+be\s+provided|to\s+avoid\s+(?:fusion|lack))',re.I)
QUALITATIVE=re.compile(
    r'(?:the\s+higher\s+the\s+energy\s+density.{0,80}?the\s+lower\s+the\s+porosity|'
    r'(?:increas(?:ing|ed)\s+energy\s+density).{0,90}?(?:decreas(?:es|ed)|lower)'
    r'.{0,25}?porosity)',re.I|re.S)


def _text(raw):
    return ' '.join(raw.split())


def _fact(kind,energy='—',density='—',porosity='—',method='No especificado en el pasaje',
          context='',span=None,priority=0,pore_size='—',hardness='—',roughness='—'):
    return {'tipo':kind,'energia':energy,'densidad':density,
            'porosidad':porosity,'tamano_poro':pore_size,'dureza':hardness,
            'rugosidad':roughness,'metodo':method,'condiciones':context,
            '_span':span,'_priority':priority}


def extract_evidence(fragment):
    """Extrae hechos tipados; los valores comparten una relación gramatical.

    El origen de un resultado (propio o estudio citado) se señala cuando la
    frase lo permite. Las magnitudes de líneas distintas NO se vinculan.
    """
    raw=_text(fragment)
    findings=[]

    for match in PAIR.finditer(raw):
        if not re.search(r'\brespectively\b',raw[match.end():match.end()+55],re.I):
            continue
        nearby=raw[max(0,match.start()-90):match.end()+100]
        context=('PBF (mencionado en el pasaje)' if re.search(
            r'\bPBF\b|powder\s+bed\s+fusion',nearby,re.I)
            else 'Condiciones no detalladas en este pasaje')
        for side in ('a','b'):
            findings.append(_fact('umbral reportado',
                energy='≥'+match.group('energy_'+side)+' J/mm³',
                density=match.group('density_'+side)+' %',
                context=context,
                span=match.span(),priority=5))

    for pattern in (RANGE_BETWEEN,RANGE_FROM):
        for match in pattern.finditer(raw):
            window=raw[max(0,match.start()-160):match.end()+80]
            method=('Análisis de imágenes' if re.search(r'image\s+analysis',window,re.I)
                    else 'No especificado en el pasaje')
            findings.append(_fact('intervalo reportado',
                energy=match.group('energy_a')+'–'+match.group('energy_b')+' J/mm³',
                density='> '+match.group('density')+' %',method=method,
                span=match.span(),priority=5))

    if not findings:
        for match in SINGLE.finditer(raw):
            tail=raw[match.end():match.end()+40]
            qualifier='≥' if re.search(r'\bor\s+higher\b',tail,re.I) else ''
            findings.append(_fact('valor reportado',
                energy=match.group('energy')+' J/mm³',
                density=qualifier+match.group('density')+' %',
                span=match.span(),priority=4))

    for match in POROSITY_ENERGY.finditer(raw):
        context=raw[max(0,match.start()-180):match.start()]
        indirect=bool(re.search(r'\bstudy\s+(?:conducted|by)|\b(?:Cherry|Tucho)\s+et\s+al',
                                context,re.I))
        equipment=re.search(r'when\s+printed\s+in\s+a\s+(.{1,70}?)\s+printer\b',
                            raw[match.end():match.end()+180],re.I)
        details=('Antecedente citado en el artículo' if indirect else '')
        if equipment:
            details+=(('; ' if details else '')+'Equipo: '+equipment.group(1).strip())
        findings.append(_fact('resultado de estudio citado' if indirect else 'valor reportado',
            energy=match.group('energy')+' J/mm³',
            porosity=match.group('porosity')+' %',
            context=details,
            span=match.span(),priority=4 if not indirect else 3))

    for match in ARCHIMEDES.finditer(raw):
        conditions=re.search(r'utiliz(?:ing|ando)\s+(.{0,135}?)(?:\.|To\s+increase)',
                             raw[match.end():match.end()+200],re.I)
        findings.append(_fact('mediciones con métodos distintos',
            density=match.group('arch')+' % (Arquímedes); '
                    +match.group('image')+' % (análisis de imágenes)',
            method='Principio de Arquímedes y correlación de imágenes',
            context=(conditions.group(1).strip() if conditions else ''),
            span=match.span(),priority=4))

    for match in OPTICAL_XCT_POROSITY.finditer(raw):
        for method,name in (('optical','Modelo óptico'),('xct','Modelo XCT')):
            findings.append(_fact('porosidad de muestras optimizadas',
                porosity=match.group(method)+' %',method=name,
                context='Muestras óptimas asociadas a modelos distintos; '
                        'verificar procedimiento de medición en el artículo',
                span=match.span(),priority=4))

    for match in METHOD_CONTRAST.finditer(raw):
        findings.append(_fact('diferencia cualitativa entre métodos',
            method='XCT y microscopía óptica',
            context=('Según este pasaje, XCT detectó mayor porosidad a baja '
                     'potencia y energía, y microscopía óptica a valores altos; '
                     'no equivale a una relación universal'),
            span=match.span(),priority=3))

    for match in PORE_SIZE_RANGE.finditer(raw):
        energy='—'
        if match.group('energy'):
            operator='<' if match.group('condition').lower()=='lower' else '>'
            energy=operator+match.group('energy')+' J/mm³'
        findings.append(_fact('intervalo de tamaño de poro',energy=energy,
            pore_size=match.group('low')+'–'+match.group('high')+' µm',
            span=match.span(),priority=4))

    for match in HARDNESS_RANGE.finditer(raw):
        findings.append(_fact('dureza reportada',
            energy='≥'+match.group('energy')+' J/mm³',
            hardness=match.group('low')+'–'+match.group('high')+' HV',
            span=match.span(),priority=4))

    for match in ROUGHNESS_VALUE.finditer(raw):
        findings.append(_fact('rugosidad reportada',
            roughness=match.group('metric')+': '+match.group('value')+' µm',
            span=match.span(),priority=3))

    for match in POROSITY_SINGLE.finditer(raw):
        # Evitar duplicar una porosidad ya asociada al mismo valor por una
        # regla más informativa, como VED-porosidad o microscopía/XCT.
        val=match.group('value')+' %'
        if any(f['porosidad']==val for f in findings):
            continue
        findings.append(_fact('porosidad reportada',porosity=val,
            span=match.span(),priority=3))

    for match in ENERGY_RECOMMENDATION.finditer(raw):
        if any(found['energia'].startswith(match.group('energy')+' ') or
               found['energia'].startswith('≥'+match.group('energy')+' ')
               for found in findings):
            continue
        findings.append(_fact('recomendación del artículo',
            energy=match.group('energy')+' J/mm³',
            context='Se recomienda para evitar defectos; sin porcentaje asociado',
            span=match.span(),priority=3))

    if not findings:
        match=QUALITATIVE.search(raw)
        if match:
            findings.append(_fact('relación cualitativa',
                context='Mayor densidad de energía asociada a menor porosidad',
                span=match.span(),priority=2))

    # Limitar resultados repetidos entre reglas sin perder dos umbrales
    # explícitamente distintos dentro de una misma oración.
    unique=[]
    seen=set()
    for fact in sorted(findings,key=lambda f:f['_priority'],reverse=True):
        key=(fact['energia'],fact['densidad'],fact['porosidad'],fact['tipo'],
             fact['tamano_poro'],fact['dureza'],fact['rugosidad'],fact['metodo'])
        if key not in seen:
            seen.add(key)
            unique.append(fact)
    return unique


def evidence_relevance(fragment,question):
    """Promueve resultados explícitos frente a introducciones bibliográficas."""
    findings=extract_evidence(fragment)
    strongest=max((f['_priority'] for f in findings),default=0)
    quantitative=sum(f['_priority']>=4 for f in findings)
    # Tres términos temáticos no deben vencer un par de resultados medidos.
    return 0.8*strongest+0.3*min(quantitative,3)


def excerpt_for_evidence(fragment,findings,limit=590):
    raw=_text(fragment)
    if len(raw)<=limit:
        return raw
    spans=[f['_span'] for f in findings if f['_span'] is not None]
    if spans:
        start,end=spans[0]
        left=max(0,start-140)
        right=min(len(raw),max(end+150,left+limit))
        if right-left>limit:
            right=left+limit
        return ('…' if left else '')+raw[left:right]+('…' if right<len(raw) else '')
    return raw[:limit]+'…'
