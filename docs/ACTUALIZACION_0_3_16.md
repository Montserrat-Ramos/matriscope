# MatriScope 0.3.16 — Progreso real en traducciones

## Qué cambia

1. Se presenta una barra de avance para cada pasaje de los PDF recuperados,
   mostrando porcentaje y número de segmentos ya traducidos y aprobados.
2. Hay un resumen general de fuentes traducidas y fuentes con fallo.
3. Los porcentajes proceden de `POST /api/traducciones`, campo `progreso`:
   `completados`, `total` y `porcentaje`. Cada llamada procesa un segmento.
   El porcentaje permanece constante mientras se ejecuta la llamada.
4. En un fallo se mantiene el avance previo y se identifica el diagnóstico.
   Cuando el servidor entrega una vista previa de la traducción rechazada,
   se presenta en un desplegable identificado expresamente como **no validada**.
5. Las traducciones protegen valores numéricos, unidades, referencias y
   ciertas fórmulas; aceptan equivalencias técnicas definidas en el glosario
   y comprueban sustituciones especialmente problemáticas (láser/lámpara,
   lecho de polvo/molde de yeso, keyhole/agujero de lluvia).

## Actualización en Windows

1. Detén MatriScope.
2. Respaldar el directorio `data/` y la configuración personalizada.
3. Extrae la versión 0.3.16 en una carpeta **nueva**. Copia `data/` de tu
   versión anterior si almacenas allí documentos y proyectos.
4. Instala dependencias si es necesario: `python -m pip install -r requirements.txt`.
5. Verifica que Ollama esté en funcionamiento y que tus modelos aparezcan en
   `ollama list`.
6. Inicia la API con:

   ```powershell
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

7. Abre `http://127.0.0.1:8010` y recarga con `Ctrl + F5`.

## Cómo comprobar la barra

- Selecciona `qwen2.5:3b` y el modo `hybrid`.
- Pregunta por la relación entre densidad de energía y porosidad del acero 316L.
- En «Fuentes recuperadas» verás los pasajes con su barra; un fragmento grande
  puede avanzar por 25 %, 50 %, 75 % y 100 %, **solo después** de cada segmento
  que superó validación. El avance exacto depende del largo del pasaje.
- Si la traducción falla, la barra se detiene, el fragmento inglés permanece
  y se muestra la razón. Puedes seleccionar `llama3.2:3b` para realizar
  una nueva consulta y comparar el comportamiento.

## Limitaciones importantes

- Un indicador al 0 % **no significa bloqueo** si Ollama todavía procesa el
  primer segmento. La barra mide trabajo terminado, no tiempo restante.
- «100 % procesadas» incluye fuentes finalizadas con fallo, claramente
  contabilizadas por separado. Cada fuente traducida tiene 100 %.
- La protección de expresiones matemáticas es selectiva: no reemplaza la
  comprobación de las tablas, fórmulas y figuras del PDF original.
- No se modifica SQLite ni la colección de embeddings. No hay que reindexar.
