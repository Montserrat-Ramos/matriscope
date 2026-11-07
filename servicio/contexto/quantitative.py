"""Síntesis extractiva limitada a relaciones cuantitativas explícitas.

No rellena citas en texto del modelo. Detecta asociaciones que aparecen en un
mismo pasaje original y crea una frase con los valores y la fuente de ese pasaje.
Si la estructura es ambigua, se abstiene de generar esa afirmación.
"""

import re
from decimal import Decimal

from servicio.contexto.retrieval import is_energy_density_question


NUMBER=r'\d+(?:[.,]\d+)?'
UNIT=r'J\s*/\s*mm\s*(?:3|³)'
FLAGS=re.IGNORECASE|re.DOTALL

PAIR=re.compile(
    rf'energy\s+densities\s+must\s+be\s+at\s+least\s+'
    rf'(?P<energy_a>{NUMBER})\s*{UNIT}\s+and\s+'
    rf'(?P<energy_b>{NUMBER})\s*{UNIT}'
    rf'.{{0,190}}?relative\s+densities\s+of\s+'
    rf'(?P<density_a>{NUMBER})\s*%\s+and\s+'
    rf'(?P<density_b>{NUMBER})\s*%',FLAGS)

RANGE_BETWEEN=re.compile(
    rf'energy\s+density\s+values\s+between\s+'
    rf'(?P<energy_a>{NUMBER})\s+and\s+'
    rf'(?P<energy_b>{NUMBER})\s*{UNIT}'
    rf'.{{0,170}}?density\s+(?:greater|higher)\s+than\s+'
    rf'(?P<density>{NUMBER})\s*%',FLAGS)

RANGE_FROM=re.compile(
    rf'from\s+(?P<energy_a>{NUMBER})\s*{UNIT}\s+to\s+'
    rf'(?P<energy_b>{NUMBER})\s*{UNIT}'
    rf'.{{0,170}}?greater\s+than\s+'
    rf'(?P<density>{NUMBER})\s*%\s+relative\s+density',FLAGS)

SINGLE=re.compile(
    rf'energy\s+density\s+is\s+(?P<energy>{NUMBER})\s*{UNIT}'
    rf'.{{0,145}}?relative\s+density\s+is\s+'
    rf'(?P<density>{NUMBER})\s*%\s*(?:or\s+higher)?',FLAGS)


def target_relative_density(question):
    """Identifica una sola densidad relativa solicitada expresamente en %."""
    if not is_energy_density_question(question):
        return None
    if not re.search(r'densidad(?:es)?\s+relativa|relative\s+densit',question,re.I):
        return None
    values=re.findall(rf'({NUMBER})\s*%',question)
    if len(values)!=1:
        return None
    return Decimal(values[0].replace(',','.'))


def extract_targeted_density_answer(question,sources):
    """Responde a una densidad relativa objetivo solo con su par documental.

    Nunca asocia cifras de documentos distintos. Para pares usa exclusivamente
    el orden que el artículo vincula mediante "respectively".
    """
    target=target_relative_density(question)
    if target is None:
        return None

    candidates=[]
    for source in sources:
        original=' '.join(source['fragmento'].split())
        paired=PAIR.search(original)
        if paired and re.search(r'\brespectively\b',original[paired.end():paired.end()+55],re.I):
            values=paired.groupdict()
            for side in ('a','b'):
                if Decimal(values['density_'+side].replace(',','.'))==target:
                    candidates.append((3,source,values['energy_'+side],'mínima'))
                    break
            continue

        single=SINGLE.search(original)
        if single and Decimal(single.group('density').replace(',','.'))==target:
            candidates.append((2,source,single.group('energy'),'reportada'))

    if not candidates:
        return None
    # Priorizar la asociación explícita de pares sobre una mención secundaria.
    strongest=max(item[0] for item in candidates)
    selected=[item for item in candidates if item[0]==strongest]
    # Presentar solo una vez el mismo resultado si hay fragmentos solapados.
    seen=set()
    lines=[]
    for _,source,energy,qualifier in selected:
        key=(source.get('documento_id',source['documento']),energy)
        if key in seen:
            continue
        seen.add(key)
        lines.append(
            f"- En las condiciones del estudio se reporta una densidad de energía "
            f"{qualifier} de {energy} J/mm³ para obtener una densidad relativa "
            f"del {target} % {source['ref']}. "
            f"({source['documento']}, pág. {source['pagina']})")

    return ('Respuesta cuantitativa extraída de relaciones explícitas en las fuentes:\n\n'
            +'\n'.join(lines)
            +'\n\nVerifica los métodos originales antes de interpretar los resultados.')


def extract_quantitative_summary(question,sources):
    """Devuelve texto con citas solo cuando hay relaciones textuales completas.

    Mantiene un resultado por documento. La asociación pareada de dos umbrales
    tiene prioridad frente a una mención parcial de un solo umbral.
    """
    if not is_energy_density_question(question):
        return None

    candidates=[]
    for source in sources:
        original=' '.join(source['fragmento'].split())
        # El patrón de dos pares tiene prioridad por preservar la relación
        # "respectively" (los dos porcentajes no son intercambiables).
        match=PAIR.search(original)
        if match and re.search(r'\brespectively\b',original[match.end():match.end()+55],re.I):
            x=match.groupdict()
            statement=(f"Se reportan densidades de energía mínimas de "
                       f"{x['energy_a']} y {x['energy_b']} J/mm³ para obtener "
                       f"densidades relativas de {x['density_a']} % y "
                       f"{x['density_b']} %, respectivamente, en las condiciones "
                       f"del estudio {source['ref']}.")
            candidates.append((3,source,statement))
            continue

        match=RANGE_BETWEEN.search(original) or RANGE_FROM.search(original)
        if match:
            x=match.groupdict()
            statement=(f"El estudio comunica un intervalo de energía de "
                       f"{x['energy_a']} a {x['energy_b']} J/mm³ con densidades "
                       f"superiores al {x['density']} % {source['ref']}.")
            candidates.append((2,source,statement))

    if not candidates:
        return None

    best_by_document={}
    for priority,source,statement in candidates:
        key=source['documento_id'] if source.get('documento_id') else source['documento']
        if key not in best_by_document or priority>best_by_document[key][0]:
            best_by_document[key]=(priority,source,statement)

    selected=list(best_by_document.values())[:4]
    lines=[
        'Resultados cuantitativos recuperados directamente de los documentos:',
        '',
    ]
    for _,source,statement in selected:
        lines.append(f"- {statement} ({source['documento']}, pág. {source['pagina']})")
    lines.extend(['',
        'Síntesis extractiva: verifica los métodos y las figuras originales antes de concluir.'])
    return '\n'.join(lines)
