# MatriScope 0.3.14 — Selector de Ollama y comparación de modelos

## Cambios disponibles

El Explorador semántico incluye tres selectores:

1. **Modelo principal:** `qwen2.5:3b` como preferido de inicio.
2. **Modo de respuesta:** `hybrid` como preferido de inicio.
3. **Segundo modelo:** `llama3.2:3b` como candidato inicial de comparación.

Los selectores también aparecen en Configuración. Sus preferencias se guardan
en el navegador, mientras que el servidor sigue gestionando top-k y embeddings.

### Qué hace cada modo

| Modo | Uso de Ollama | Protección científica |
| --- | --- | --- |
| `hybrid` | Solo si la extracción no resuelve la pregunta | Extracción preferente, guardrails y abstención |
| `generative` | Sí, salvo consulta fuera de alcance o evidencia insuficiente | Citas obligatorias, verificación de magnitudes, corrección extractiva de pares exactos |
| `extractive` | No usa un LLM para responder | Relaciones textuales explícitas o abstención |

Las consultas fuera de alcance (ej. «¿cuánto es 2+2?») siguen rechazadas antes
de recuperar fragmentos. El filtro de alcance puede consultar un LLM si el
ámbito temático es incierto; esto es independiente del **modo de respuesta**.

El botón **Comparar modelos** envía la misma pregunta a ambos modelos en modo
`generative`, secuencialmente, con el mismo corpus, top-k y políticas de citas.
La comparación presenta las dos respuestas, modelo ejecutado, tiempo, estado,
validación y fuentes. No implica una comparación científica certificada.

## Instalación sin perder los PDF

1. Detener MatriScope y **respaldar** la carpeta `data/` y cualquier `.env`.
2. Extraer la versión 0.3.14 en una carpeta distinta, sin sobrescribir la
   versión previa. Copiar `data/` de la versión anterior a esta carpeta.
3. Instalar los modelos de lenguaje si faltan:

   ```powershell
   ollama pull qwen2.5:3b
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text
   ollama list
   ```

4. Desde el directorio `matriscope-app`:

   ```powershell
   python -m pip install -r requirements.txt
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

5. Abrir `http://127.0.0.1:8010` y actualizar con `Ctrl + F5`.
6. Consultar `http://127.0.0.1:8010/api/modelos` para ver modelos instalados.
7. En el Explorador, escoger `qwen2.5:3b` y `hybrid`.

## Comprobaciones sugeridas

| Prueba | Resultado esperado |
| --- | --- |
| «¿Cuánto es 2+2?» | `fuera_de_alcance`, sin citas irrelevantes |
| «¿Qué energía corresponde a 99.9 % de densidad relativa en el estudio?» | `hybrid`: extracción si el par 103 J/mm³ / 99.9 % está en un pasaje |
| La misma pregunta con `generative` | Ejecuta el modelo elegido, preserva el par cuantitativo exacto y exige citas |
| Pregunta de porosidad con `extractive` | Explicación documental explícita o abstención sin LLM de respuesta |
| **Comparar modelos** con pregunta documental | Dos resultados con trazas individuales; revisión humana obligatoria |
| Seleccionar modelo no instalado | Error 422 con nombre de modelo y comando `ollama pull` |

Si un modelo no genera citas suficientes, MatriScope puede reintentar y
presentar fragmentos de respaldo. El hecho de que una cita exista no confirma
automáticamente la interpretación científica.

**Alcance y límites:** la ejecución y rendimiento de `qwen2.5:3b` deben
comprobarse en el equipo local; las pruebas automatizadas usan modelos
simulados. No se modificó la base de datos ni el mecanismo de traducción
progresiva de 0.3.13.
