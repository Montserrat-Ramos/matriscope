# MatriScope v0.3.18 — Comparación dirigida y protección de ecuaciones

## Caso que originó la corrección

Pregunta: «¿Equivale recomendar 125 J/mm³ en JMMP a garantizar >99.8 % en
todo el intervalo 45–125 J/mm³ de Metals?».

El resultado anterior invocaba a Qwen y recuperaba fuentes de Materials y
JMMP, pero no seleccionaba el artículo de Metals necesario. Además, un PDF
contenía símbolos de fórmula extraídos como caracteres de control.

## Qué cambia

1. **Clasificación:** «equivale» y «garantiza» activan el tratamiento de
   comparación documental. En modo `hybrid`, si las relaciones son reconocibles,
   se aplica extracción y no se necesita invocar un LLM para redactar.
2. **Búsqueda por publicación:** cuando se nombran dos familias de documentos
   del proyecto, MatriScope realiza recuperación por cada familia y da un
   lugar a ambas. Los nombres se detectan a partir de los archivos del corpus,
   sin depender de una lista fija de revistas.
3. **Selección:** si hay varias publicaciones `metals-*.pdf`, el ranking utiliza
   las cifras de la pregunta junto con los resultados extraídos para priorizar
   el pasaje pertinente. No se asume automáticamente que todos los archivos
   de una revista son el mismo estudio.
4. **Cobertura:** el resultado incluye las publicaciones solicitadas,
   recuperadas y faltantes. Si falta una, se abstiene de comparar usando otra
   como sustituta.
5. **Equivalencia científica:** una recomendación y un intervalo de otro
   artículo no se presentan como garantías intercambiables. La matriz mantiene
   magnitudes, métodos y citas por fuente.
6. **Ecuaciones PDF:** si un segmento contiene caracteres de control que
   indican extracción matemática ilegible, la traducción se marca con
   `ecuacion_pdf_no_interpretable` y se deja visible el fragmento original.
   Reintentar otro LLM no repara esos caracteres; debe consultarse el PDF.

## Cómo instalar en Windows

1. Detén el servidor actual y respalda tu directorio de datos.
2. Extrae la nueva versión en otra carpeta; conserva los proyectos y archivos
   en su ubicación de datos previa o copia el directorio `data/` si aplica.
3. Comprueba `ollama list` y, desde la carpeta `matriscope-app`, ejecuta:

   ```powershell
   python -m pip install -r requirements.txt
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

4. Recarga `http://127.0.0.1:8010` con `Ctrl + F5`.

## Comprobación recomendada

1. Ejecuta la pregunta JMMP–Metals anterior con `qwen2.5:3b` y `hybrid`.
2. En «Cobertura de publicaciones solicitadas» deben aparecer `jmmp` y
   `metals`; si hay pasajes pertinentes, la matriz debe incluir fuentes de
   ambos estudios. No debe sustituir el artículo de Metals por Materials.
3. Comprueba que las recomendaciones de 125 J/mm³ y los intervalos con
   densidad relativa se presenten con su artículo de origen, nunca como una
   garantía universal.
4. En pasajes con ecuaciones mal extraídas, verifica que se informe el motivo
   y se conserve el inglés en lugar de reconstruir números o símbolos.

## Alcance y límites

- La selección dirigida se aplica a publicaciones identificadas por el nombre
  del archivo. Nombres ambiguos o inexistentes requieren verificación humana.
- Los patrones extractivos no reconocen todos los resultados científicos.
  Una abstención sigue siendo posible con pasajes insuficientes.
- No se modifican los documentos, la base SQLite ni los vectores existentes.
  El cambio de versión invalida la caché de respuestas antiguas por revisión
  del algoritmo; **no hace falta reindexar**.
- Las pruebas locales automatizadas no sustituyen la ejecución real con los
  cinco artículos y Ollama en la computadora de la usuaria.
