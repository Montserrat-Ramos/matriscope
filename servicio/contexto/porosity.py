"""Relaciones energía–porosidad explícitas, preservando condiciones y citas.

Las reglas reconocen afirmaciones delimitadas; jamás convierten la densidad
relativa en porosidad ni convierten resultados de artículos en leyes generales.
"""

import re


_ENERGY=r'\d+(?:[.,]\d+)?\s*J\s*/\s*mm\s*(?:3|³)'
_LOW=re.compile(
    rf'(?:energy\s+density|volumetric\s+energy\s+density|\bVED\b)'
    rf'.{{0,95}}?\b(?:below|less\s+than|under)\s*(?P<value>{_ENERGY})'
    rf'.{{0,160}}?(?:lack.of.fusion|insufficient\s+melting)',re.I|re.S)
_HIGH=re.compile(
    rf'(?:excessive\s+energy\s+density|energy\s+density|\bVED\b)'
    rf'.{{0,95}}?\b(?:above|greater\s+than|over)\s*(?P<value>{_ENERGY})'
    rf'.{{0,130}}?\bkeyhole\b',re.I|re.S)
_DECREASING=re.compile(
    r'(?:the\s+higher\s+the\s+(?:volumetric\s+)?energy\s+density\s*,?\s*'
    r'the\s+lower\s+the\s+(?:sectional\s+)?porosity|'
    r'(?:higher|increased)\s+energy\s+density.{0,75}?'
    r'(?:lower|decreased|reduced)\s+porosity|'
    r'a\s+mayor\s+densidad\s+(?:de\s+)?energ[ií]a.{0,70}?'
    r'menor\s+porosidad)',re.I|re.S)
_RELEVANCE=re.compile(r'porosidad|porosity|pores?',re.I)
_QUESTION=re.compile(r'energ[ií]a|energy|\bved\b',re.I)


def is_energy_porosity_question(question):
    """Distingue la propiedad porosidad de una mera densidad relativa."""
    return bool(_QUESTION.search(question) and re.search(
        r'porosidad|porosity|defectos?\s+por\s+fusi[oó]n',question,re.I))


def extract_energy_porosity_explanation(question,sources):
    """Hasta dos observaciones complementarias de artículos distintos.

    Solo genera una observación cuando la relación física está expresamente
    descrita dentro del fragmento de la misma fuente.
    """
    if not is_energy_porosity_question(question):
        return None

    trends=[]
    regimes=[]
    for source in sources:
        original=' '.join(source['fragmento'].split())
        if not (_QUESTION.search(original) and _RELEVANCE.search(original)):
            continue
        low=_LOW.search(original)
        high=_HIGH.search(original)
        if low and high:
            low_value=re.sub(r'\s*J\s*/\s*mm\s*(?:3|³)',
                             ' J/mm³',low.group('value'),flags=re.I)
            high_value=re.sub(r'\s*J\s*/\s*mm\s*(?:3|³)',
                              ' J/mm³',high.group('value'),flags=re.I)
            regimes.append((source,
                f"El artículo describe defectos por falta de fusión con "
                f"densidad energética inferior a {low_value}, y porosidad "
                f"asociada al modo keyhole por encima de {high_value} "
                f"{source['ref']}."))
        if _DECREASING.search(original):
            trends.append((source,
                f"Dentro de las condiciones estudiadas, los autores "
                f"describen una disminución de la porosidad al aumentar "
                f"la densidad de energía {source['ref']}."))

    results=[]
    used=set()
    # El contraste bajo/excesivo evita presentar una tendencia monótona
    # como si aplicara a cualquier energía o impresora.
    for candidates in (trends,regimes):
        for source,statement in candidates:
            doc=source.get('documento_id') or source['documento']
            if doc not in used:
                results.append((source,statement))
                used.add(doc)
                break

    if not results:
        return None
    lines=['Relaciones energía–porosidad identificadas explícitamente en las fuentes:', '']
    for source,statement in results:
        lines.append(f"- {statement} ({source['documento']}, pág. {source['pagina']})")
    lines.extend(['', 'Revisa las condiciones experimentales antes de comparar los estudios.'])
    return '\n'.join(lines)
