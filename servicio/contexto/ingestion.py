"""Lectura documental y segmentación por página para preservar fuentes."""

from io import BytesIO

from pypdf import PdfReader


class DocumentError(ValueError):
    pass


def extract_pages(contents: bytes, filename: str):
    if filename.lower().endswith('.pdf'):
        if not contents.startswith(b'%PDF-'):
            raise DocumentError('El archivo no tiene la firma esperada de PDF.')
        try:
            reader = PdfReader(BytesIO(contents))
            if reader.is_encrypted:
                raise DocumentError('PDF cifrado: debe proporcionarse una versión autorizada legible.')
            pages = [(i+1, (page.extract_text() or '').strip()) for i,page in enumerate(reader.pages)]
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError(f'No se pudo extraer texto del PDF: {exc}') from exc
    elif filename.lower().endswith(('.txt','.md')):
        try:
            pages = [(1,contents.decode('utf-8-sig').strip())]
        except UnicodeDecodeError as exc:
            raise DocumentError('El archivo de texto debe estar en UTF-8.') from exc
    else:
        raise DocumentError('Formato no admitido; usa PDF con texto, TXT o Markdown.')
    if not any(text for _,text in pages):
        raise DocumentError('El documento no contiene texto extraíble. Se requiere OCR verificado.')
    return pages


def chunk_pages(pages, size=850, overlap=120):
    """Fragmentos de caracteres por página; ajustes sujetos a evaluación."""
    if size < 100 or overlap < 0 or overlap >= size:
        raise ValueError('Tamaño o solapamiento inválidos.')
    chunks=[]
    for page,text in pages:
        cleaned=' '.join(text.split())
        start=0
        while start < len(cleaned):
            end=min(start+size,len(cleaned))
            if end<len(cleaned):
                boundary=cleaned.rfind(' ',start+size//2,end)
                if boundary>start+size//2:end=boundary
            fragment=cleaned[start:end].strip()
            if len(fragment)>=30:
                chunks.append({'page':page,'content':fragment})
            if end>=len(cleaned):break
            start=max(start+1,end-overlap)
    return chunks

