# MatriScope 0.3.12 — Síntesis científica y traducción documental

## Motivación: prueba P03

La pregunta por la relación entre densidad volumétrica de energía y porosidad
recuperaba fragmentos relevantes, pero al fallar el LLM en el formato de citas
se mostraba solo el par 79/103 J/mm³ asociado a densidad **relativa**. Faltaba
explicar por qué pueden aparecer poros tanto por energía insuficiente como
por energía excesiva.

## Mejoras

1. **Relaciones científicas expresas**: nueva extracción contextual de la
   disminución de porosidad al aumentar la energía *dentro del intervalo
   estudiado* y de mecanismos de falta de fusión/keyhole en extremos.
2. **Múltiples documentos**: si los pasajes sustentan ambos tipos de
   observación, se citan dos estudios diferentes, cada uno con su página.
3. **Sin inferencias nuevas**: no se mezclan porosidad y densidad relativa,
   no se interpolan cifras, ni se convierten rangos particulares en reglas
   físicas universales. Cuando faltan relaciones explícitas se mantiene el
   comportamiento anterior.
4. **Recuperación enfocada**: preguntas sobre energía y porosidad priorizan
   fragmentos con mecanismos descritos; preguntas por un porcentaje concreto
   de densidad relativa conservan su selección previa.
5. **Traducción al español**: la interfaz solicita una traducción local de
   hasta cinco fragmentos recuperados. Muestra el español y permite desplegar
   el texto original en inglés. No modifica los PDFs ni los textos indexados.
6. **Control numérico de traducción**: si se pierden o modifican números o
   unidades, la traducción se descarta para ese pasaje y se conserva el original.
   La revisión científica sigue siendo obligatoria: el control no garantiza
   equivalencia semántica completa.
7. **Traducción no bloqueante**: si Ollama tarda, la respuesta RAG aparece
   primero. La traducción llega después; si Ollama falla, el original queda
   visible. Las traducciones verificadas se reutilizan en memoria hasta
   reiniciar el servicio.

## Cómo actualizar

1. Detén Uvicorn con `Ctrl + C`.
2. Crea una copia de seguridad de tu carpeta `data/` y archivo `.env`.
3. Extrae la versión 0.3.12 en **una carpeta nueva**.
4. Copia los datos de tu instalación anterior a la carpeta nueva, sin borrar
   ni modificar los originales.
5. Ejecuta `python -m pip install -r requirements.txt` si todavía no has
   instalado los requisitos en el entorno virtual seleccionado.
6. Ejecuta desde `matriscope-app`:

   ```powershell
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

7. Verifica `0.3.12` en `http://127.0.0.1:8010/openapi.json`, recarga la
   página con `Ctrl + F5` y repite P03.

**No es necesario reindexar documentos ni migrar SQLite.**

## Pregunta P03 recomendada

> ¿Qué relación existe entre la densidad volumétrica de energía y la
> porosidad del acero inoxidable 316L fabricado mediante LPBF, según los
> artículos científicos cargados?

Comprobar:

- Si los fragmentos seleccionados sustentan las dos relaciones, la respuesta
  incluye **tendencia dentro del estudio** y **mecanismos en extremos**.
- Cada afirmación lleva una cita `[F#]` correspondiente a su propio documento.
- Los pasajes se muestran primero en español cuando termina la traducción;
  el original aparece al desplegar «Ver fragmento original (inglés)».
- El apartado de traducción puede tardar más que la respuesta principal.
- Los valores 46/127 J/mm³ son únicamente un ejemplo del corpus 316L; **no**
  se guardaron como respuestas fijas en el programa.

## Limitaciones conocidas

- El extractor cubre relaciones redactadas con patrones explícitos. Otros
  documentos, figuras, tablas u otras formulaciones todavía pueden activar
  la síntesis de Ollama y sus guardrails originales.
- La traducción es automática con `llama3.2:3b`; los términos científicos
  deben verificarse antes de utilizarse en un trabajo académico.
- La validación técnica es local con pruebas simuladas. El comportamiento
  final debe contrastarse con los cinco PDFs y Ollama instalados en Windows.
