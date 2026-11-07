# MatriScope 0.3.11 — Validación del alcance documental

## Problema observado

La pregunta «¿Cuánto es 2+2?» iniciaba la búsqueda vectorial y recuperaba
pasajes sin relación (porosidad, energía, fabricación LPBF), después intentaba
generar citas. Un RAG científico cerrado no debe contestar con conocimientos
generales ni mostrar esos fragmentos para una pregunta externa al corpus.

## Cambios implementados

1. Nuevo `servicio/contexto/scope.py` con filtro previo a embeddings,
   recuperación, generación y caché.
2. Las operaciones aritméticas aisladas se clasifican directamente como
   `FUERA`, sin consultas a Ollama. Si se pregunta explícitamente por
   una operación **descrita en un PDF**, el patrón estricto no se activa.
3. Para los casos no obvios, se contrastan los términos con el nombre,
   descripción y archivos del proyecto. Cuando no hay coincidencia, Ollama
   puede clasificar el alcance a partir de muestras de documentos locales.
   La única salida aceptada es `DENTRO`, `FUERA` o `INCIERTO`; una salida
   imprevista o indisponibilidad del modelo se trata como incierta.
4. Para preguntas `FUERA`, la API devuelve `fuera_de_alcance`, abstención
   y cero fuentes, búsquedas e intentos de generación.
5. La interfaz oculta «Fuentes recuperadas» para este estado y presenta
   el aviso de que MatriScope consulta exclusivamente los documentos del
   proyecto.

## Comportamiento esperado

| Consulta | Resultado esperado |
| --- | --- |
| ¿Cuánto es 2+2? | `fuera_de_alcance`, sin LLM ni búsqueda |
| ¿Qué capital tiene Francia? (corpus LPBF/316L) | `fuera_de_alcance` si la clasificación textual lo confirma |
| ¿Qué energía reportan los documentos para 99.9 % de densidad relativa? | Consulta RAG y evidencia citada, si se recupera |
| ¿Qué energía produce exactamente una densidad de 99.7 %? | Consulta RAG, sin inventar o interpolar la relación |
| ¿Qué dice el PDF sobre un resultado que no aparece? | Consulta RAG; abstención por evidencia insuficiente |

## Limitaciones y pruebas pendientes

- El filtro no convierte una respuesta científica en fiable: sigue siendo
  necesario verificar citas, métodos, tablas y condiciones experimentales.
- La clasificación con `llama3.2:3b` puede equivocarse. Ejecutar una batería
  equilibrada de preguntas relevantes, irrelevantes y ambiguas con los PDF
  reales, y anotar los errores de alcance para ajustar el clasificador.
- El muestreo por documento usa un fragmento inicial: las preguntas que
  conciernen páginas posteriores pueden clasificarse como inciertas.
- Este cambio no requiere migración de SQLite ni reindexar documentos.

## Instalación en una versión previa

1. Detener el servicio.
2. Guardar copia de seguridad de `data/` y del archivo `.env`, si existe.
3. Sustituir únicamente los archivos de código por los de este paquete,
   **sin borrar ni reemplazar** `data/`, `.env` ni PDFs propios.
4. Iniciar Ollama y el servidor como indica el README.
5. Comprobar los casos de la tabla en el Explorador semántico.
6. Comprobar que `http://127.0.0.1:8010/openapi.json` informe versión
   `0.3.11`. Si el navegador conserva la interfaz anterior, usar `Ctrl + F5`.
