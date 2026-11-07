# MatriScope v0.3.21 — Generación estructurada y traducción focalizada

## Incidente

En la prueba anterior, Qwen2.5 3B recibió dos pasajes relevantes de
JMMP y Metals, pero sus dos respuestas fueron rechazadas por párrafos
sin citas. Además, al traducir Metals, el modelo deformó marcadores de
números de año, página y figuras presentes en el texto extraído.

## Cambios principales

1. Las comparaciones con Ollama usan ahora su modo JSON. El modelo debe
   proporcionar afirmaciones y una conclusión con un campo `fuentes`
   que contiene únicamente identificadores de pasajes recuperados.
2. El servicio compone la presentación a partir de esos campos, sin
   inventar ni agregar etiquetas que el modelo no haya declarado.
3. Las mismas validaciones comprueban los valores, la existencia de las
   referencias, que se hayan cubierto ambos estudios y que la conclusión
   no afirme equivalencia universal sin evidencia.
4. Si la estructura falla, existe un reintento. Si falla nuevamente,
   se descarta la generación y queda la comparación extractiva segura.
5. Para fuentes extensas con resultados cuantitativos reconocibles, la
   traducción usa el pasaje próximo a los resultados. Se indica
   `Traducción del pasaje pertinente (fragmento abreviado)` y se
   conserva el original completo en inglés.

## Prueba local

1. Detén MatriScope y haz una copia de seguridad del directorio de datos.
2. Reemplaza los archivos del programa por esta versión, sin borrar
   SQLite ni los PDF indexados.
3. Reinicia la API y comprueba que Ollama esté disponible.
4. Selecciona `qwen2.5:3b`, modo `hybrid`.
5. Pregunta:

   ¿Equivale recomendar 125 J/mm³ en JMMP a garantizar una densidad
   superior al 99.8 % en todo el intervalo 45–125 J/mm³ de Metals?

Si Qwen produce una comparación válida, deberán aparecer su nombre y
el resumen razonado con citas junto a la matriz de evidencia. Si no
logra hacerlo, se rechazará expresamente; esto es una medida de
seguridad, no un fallo de conexión.

No se requiere reindexar.

## Pruebas automatizadas

```bash
python -m unittest discover -s tests -p 'test_*.py' -q
node --test tests/test_web_ui.cjs
```
