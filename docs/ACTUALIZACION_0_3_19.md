# MatriScope v0.3.19 — Comparaciones razonadas con respaldo documental

## Por qué se realizó el cambio

En versiones anteriores, `hybrid` generaba una comparación documental
extractiva y salía antes de consultar Ollama, incluso si la usuaria
había seleccionado `qwen2.5:3b`. Esto se mostraba como
`Modelo de respuesta: No utilizado (extracción documental)`.

Ahora, **en preguntas comparativas**, `hybrid` y `generative` ejecutan
el modelo seleccionado. El modo `extractive` permanece sin generación.

## Nuevas protecciones

1. Ollama recibe pasajes pertinentes por fuente y resultados extraídos
   sin mezclar las magnitudes entre publicaciones.
2. Cada afirmación generativa debe incluir referencias válidas. Las
   magnitudes con unidades deben aparecer en las fuentes citadas.
3. La comparación debe mencionar con referencias al menos dos artículos.
   Si la usuaria solicita JMMP y Metals, ambos deben estar citados.
4. La conclusión que responde a «¿Equivale...?» o «¿Garantiza...?»
   debe citar las publicaciones involucradas.
5. Una respuesta inválida se reintenta una vez con el mismo modelo.
   Si falla, se muestra la evidencia extractiva como respaldo, sin
   presentarla como una conclusión generada aprobada.
6. La matriz de evidencia y los originales en inglés siguen accesibles.
7. Se reducen pasajes repetidos de la misma publicación y se penalizan
   tablas de composición que no respondan a la pregunta de comparación.

Estos controles verifican consistencia formal, no equivalencia científica.
Es indispensable la revisión humana de métodos, máquinas y muestras.

## Actualización local en Windows

1. Detén el servicio MatriScope.
2. Haz respaldo de la carpeta con los datos SQLite y los PDFs originales.
3. Sustituye el código anterior por los archivos de esta versión;
   conserva tu directorio de datos y configuración local.
4. Inicia MatriScope como indica el README.
5. Comprueba que Ollama esté ejecutándose y que `qwen2.5:3b` aparezca
   entre los modelos instalados.
6. En Explorador, usa `hybrid` y prueba:

   ¿Equivale recomendar 125 J/mm³ en JMMP a garantizar más de
   99.8 % en todo el intervalo 45–125 J/mm³ de Metals?

Deberías ver «Modelo de respuesta: qwen2.5:3b» si la comparación
dispone de evidencia suficiente, el modelo responde y se ejecuta
correctamente. La matriz sigue visible para cotejar la respuesta.
Si la generación no supera los controles, el sistema informa el
rechazo y conserva la evidencia original.

No requiere volver a indexar documentos.

## Comprobación automatizada

```bash
python -m unittest discover -s tests -p 'test_*.py' -q
node --test tests/test_web_ui.cjs
```
