"""Exportación de evidencia validada a PDF, sin conclusiones inventadas."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)


class ReportNotReady(ValueError):
    pass


def _fonts():
    candidate=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    bold=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    if candidate.exists() and bold.exists():
        if 'MatriDejaVu' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('MatriDejaVu',str(candidate)))
            pdfmetrics.registerFont(TTFont('MatriDejaVuBold',str(bold)))
            pdfmetrics.registerFontFamily('MatriDejaVu',normal='MatriDejaVu',bold='MatriDejaVuBold')
        return 'MatriDejaVu','MatriDejaVuBold'
    return 'Helvetica','Helvetica-Bold'


def create_pdf(analysis,project):
    """Devuelve los bytes PDF; exige al menos una afirmación revisada favorablemente.

    Quien invoca debe comprobar que las fuentes documentales siguen disponibles.
    """
    claims=[(idx,item) for idx,item in enumerate(analysis['afirmaciones'],start=1)
            if (item.get('revision') or {}).get('verdict') in {'aceptada','corregida'}]
    if not claims:
        raise ReportNotReady('No hay afirmaciones aprobadas o corregidas para exportar.')
    sources={source['ref']:source for source in analysis.get('fuentes',[])}
    for _,claim in claims:
        if not claim.get('fuentes') or any(ref not in sources for ref in claim['fuentes']):
            raise ReportNotReady('Una afirmación aprobada perdió sus referencias verificables.')

    regular,bold=_fonts()
    navy=colors.HexColor('#19283f')
    cyan=colors.HexColor('#008f9b')
    gray=colors.HexColor('#586779')
    line=colors.HexColor('#e1e8ee')
    styles={
        'eyebrow':ParagraphStyle('eyebrow',fontName=bold,fontSize=8,textColor=cyan,leading=12,spaceAfter=13),
        'title':ParagraphStyle('title',fontName=bold,fontSize=21,leading=27,textColor=navy,spaceAfter=14),
        'h':ParagraphStyle('h',fontName=bold,fontSize=12,textColor=navy,leading=17,spaceBefore=16,spaceAfter=9),
        'body':ParagraphStyle('body',fontName=regular,fontSize=9.2,leading=15,textColor=navy,spaceAfter=8),
        'small':ParagraphStyle('small',fontName=regular,fontSize=8,leading=12,textColor=gray,spaceAfter=7),
        'claim':ParagraphStyle('claim',fontName=bold,fontSize=10,leading=16,textColor=navy,spaceAfter=7),
        'center':ParagraphStyle('center',fontName=regular,fontSize=8.2,leading=12,textColor=gray,alignment=TA_CENTER),
    }
    paragraph=lambda value,key='body':Paragraph(escape(str(value or '—')),styles[key])
    page_width,page_height=A4
    buffer=BytesIO()

    def decorated_page(canvas,doc):
        canvas.saveState()
        canvas.setFillColor(navy)
        canvas.rect(0,page_height-11,page_width,11,fill=1,stroke=0)
        canvas.setStrokeColor(line)
        canvas.line(42,46,page_width-42,46)
        canvas.setFont(regular,8)
        canvas.setFillColor(gray)
        canvas.drawString(42,32,'MatriScope  |  Informe de evidencia revisada  |  Ejecución local')
        canvas.drawRightString(page_width-42,32,f'Página {doc.page}')
        canvas.restoreState()

    document=BaseDocTemplate(buffer,pagesize=A4,leftMargin=42,rightMargin=42,
                             topMargin=57,bottomMargin=64,
                             title='MatriScope - Informe de evidencia revisada',
                             author='MatriScope - Revisión humana registrada')
    document.addPageTemplates(PageTemplate(id='normal',
        frames=[Frame(42,64,page_width-84,page_height-121,leftPadding=0,
                      rightPadding=0,topPadding=0,bottomPadding=0)],onPage=decorated_page))

    story=[paragraph('MAT RISCOPE  /  INTELIGENCIA CIENTÍFICA'.replace('MAT RISCOPE','MATRISCOPE'),'eyebrow'),
           paragraph('Informe de evidencia revisada','title'),
           paragraph(f"Proyecto: {project['name']}"),
           paragraph(f"Pregunta: {analysis['pregunta']}"),
           paragraph(f"Análisis: {analysis['id']}  |  Fecha UTC: {analysis['fecha']}",'small'),
           paragraph(f"Traza: {analysis['traza_id']}  |  Modelo generador: {analysis.get('modelo') or 'sin registro'}",'small'),
           Spacer(1,5),
           paragraph('Alcance y límites de interpretación','h'),
           paragraph('Este documento contiene exclusivamente afirmaciones con decisión humana '
                     '"aceptada" o "corregida" registrada en MatriScope. La aceptación es una '
                     'declaración de quien revisó, no una certificación externa ni una validación '
                     'automática de hechos. Las afirmaciones pendientes y rechazadas se excluyen.'),
           paragraph('No se infiere causalidad, equivalencia de condiciones experimentales '
                     'ni generalización entre estudios sin evidencia adicional. Verificar '
                     'los artículos originales antes de publicar resultados.','small')]
    if analysis.get('corpus_modificado'):
        story.append(paragraph('Advertencia: el corpus del proyecto cambió desde que se '
                               'generó este análisis. Revisar la vigencia de las fuentes.','body'))

    tally=analysis['resumen_revision']
    data=[[paragraph('Aprobadas','small'),paragraph('Corregidas','small'),
           paragraph('Pendientes','small'),paragraph('Rechazadas','small')],
          [str(tally['aceptada']),str(tally['corregida']),str(tally['pendiente']),str(tally['rechazada'])]]
    table=Table(data,colWidths=[(page_width-84)/4]*4)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f1f6f9')),
                               ('GRID',(0,0),(-1,-1),0.4,line),
                               ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                               ('TOPPADDING',(0,0),(-1,-1),9),
                               ('BOTTOMPADDING',(0,0),(-1,-1),9)]))
    story.extend([table,paragraph('Afirmaciones incluidas y revisión','h')])
    referenced={ref for _,claim in claims for ref in claim['fuentes']}
    for index,claim in claims:
        review=claim['revision']
        final_text=review['corrected_text'] if review['verdict']=='corregida' else claim['texto']
        story.append(KeepTogether([
            paragraph(f"Afirmación {index} · {review['verdict'].capitalize()}",'h'),
            paragraph(final_text,'claim'),
            paragraph('Referencias: '+', '.join(claim['fuentes']),'small'),
            paragraph(f"Revisor declarado: {review['reviewer']}  |  Fecha UTC: {review['created_at']}",'small'),
            paragraph('Justificación de revisión: '+review['comment'],'body'),
        ]))
    story.append(paragraph('Fuentes documentales citadas','h'))
    for ref,source in sources.items():
        if ref not in referenced:
            continue
        story.extend([paragraph(f"{ref}  {source.get('documento','Documento')}",'claim'),
                      paragraph('Página: '+str(source.get('pagina','—'))+
                                '  |  DOI: '+str(source.get('doi') or 'No declarado'),'small'),
                      paragraph('Fragmento recuperado: '+str(source.get('fragmento','')),'body'),
                      Spacer(1,6)])
    story.extend([paragraph('Trazabilidad y reproducción','h'),
                  paragraph('Los identificadores de análisis, traza y documentos permiten '
                            'buscar los registros en la instalación local. El historial '
                            'de revisiones permanece en SQLite y no se sobrescribe.'),
                  paragraph('Limitación de identidad: los nombres de revisores son declarados '
                            'manualmente; esta versión no implementa autenticación.','small')])
    document.build(story)
    return buffer.getvalue()
