# MatriScope v0.3.20 — Validación clara y menor ruido en fuentes

## Incidente observado

La consulta de equivalencia entre JMMP y Metals recuperó el estudio de
cada publicación, pero Qwen no superó la validación de citas tras dos
intentos. Además, la página 12 de Metals aportó un bloque de cifras
tabulares con valores repetidos como `0.03` y `0.12`. La traducción
automática intentó traducirlo como prosa y produjo una lista extensa
de números ausentes y marcadores dañados.

## Cambios

1. Para preguntas concretas de equivalencia, si la evidencia extractiva
   ya respalda ambos artículos, se selecciona un pasaje por publicación.
   Se conserva siempre la opción de revisar cada PDF original.
2. Los pasajes dominados por números de tablas o gráficas quedan en
   inglés y se informa que deben comprobarse en la página del PDF.
   No se simula una traducción ni se marcan todos sus números como
   errores del modelo.
3. La comparación de diferencias de traducción agrega repeticiones:
   `0.03 (7 veces)` en vez de listar el mismo número siete veces.
4. Las referencias explícitas escritas como `[F1, F2]` se convierten
   en `[F1] [F2]`. Si Ollama añade un prefacio sin evidencia, el
   sistema puede conservar únicamente sus afirmaciones que ya
   incluyan citas. Las afirmaciones resultantes siguen pasando las
   validaciones de magnitudes, cobertura y conclusión comparativa.
5. Si Qwen aún falla dos veces, se mantiene el rechazo; sin embargo,
   el usuario puede leer también la comparación extractiva junto
   a la matriz en la pantalla, sin que se atribuya al modelo
   una respuesta generativa no validada.

Estos controles reducen errores de formato y OCR. No validan por sí
solos una conclusión científica: sigue siendo obligatorio revisar
condiciones y métodos experimentales.

## Cómo actualizar en Windows

1. Detén MatriScope.
2. Conserva una copia de los datos SQLite, PDFs y configuración local.
3. Sustituye los archivos de código por los incluidos en este ZIP.
4. Inicia el servicio como indica el README.
5. Selecciona `qwen2.5:3b`, modo `hybrid`, y repite:

   ¿Equivale recomendar 125 J/mm³ en JMMP a garantizar una densidad
   superior al 99.8 % en todo el intervalo 45–125 J/mm³ de Metals?

El objetivo es recuperar el pasaje de JMMP y el pasaje de Metals,
ejecutar el modelo con esas evidencias y aceptar la explicación
únicamente si respeta las citas y los resultados originales.
Si falla, seguirá mostrándose la matriz y la explicación extractiva.

No necesitas reindexar los PDF.

## Pruebas automatizadas

```bash
python -m unittest discover -s tests -p 'test_*.py' -q
node --test tests/test_web_ui.cjs
```
