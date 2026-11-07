# MatriScope · Fase 3: evaluación experimental integrada

## Objetivo del producto

La plataforma incorpora ahora una unidad de experimentación para verificar su
comportamiento sobre **corpus real etiquetado por una persona**, sin publicar
números simulados como evidencia científica.

## Componentes

| Elemento | Archivo | Responsabilidad |
|---|---|---|
| API de evaluaciones | `servicio/api/main.py` | Casos, activación, ejecuciones, detalles y resultados. |
| Motor de pruebas | `servicio/evaluacion/runner.py` | Modelos, embeddings, ranking, métricas y ejecución en segundo plano. |
| Almacén | `servicio/datos/sqlite_store.py` | Casos, snapshots, ejecuciones, vectores y resultados. |
| Adaptador local | `servicio/datos/ollama.py` | Chat, embeddings y digests de modelos locales. |
| Pantalla | `web/live.js` | Formularios, progreso, comparativas e inspección por caso. |

## Contratos de API

| Verbo | Ruta | Propósito |
|---|---|---|
| GET | `/api/evaluaciones/casos?project_id=ID` | Listar casos etiquetados. |
| POST | `/api/evaluaciones/casos` | Registrar caso con fuentes humanas. |
| PATCH | `/api/evaluaciones/casos/ID` | Activar o desactivar caso sin eliminarlo. |
| POST | `/api/evaluaciones/ejecuciones` | Iniciar comparación controlada, HTTP 202. |
| GET | `/api/evaluaciones/ejecuciones?project_id=ID` | Historial y métricas por combinación. |
| GET | `/api/evaluaciones/ejecuciones/ID` | Registro completo con respuestas y fuentes. |
| GET | `/api/evaluaciones/ejecuciones/ID.csv` | Exportar resultados verificables para análisis externo. |

Ejemplo de caso positivo:

```json
{
  "project_id": "ID_DEL_PROYECTO",
  "pregunta": "¿Qué reportan los documentos sobre la porosidad del 316L?",
  "documentos_relevantes": ["ID_REAL_DE_UN_DOCUMENTO_DEL_PROYECTO"],
  "sin_evidencia": false,
  "nota_referencia": "Criterio de referencia redactado por una revisora."
}
```

Para un caso negativo se usa `documentos_relevantes: []` y
`sin_evidencia: true`. El conjunto real se incorpora mediante la interfaz,
no mediante respuestas prellenadas.

## Comparación justa y métricas

Se ejecutan cuatro condiciones: (LLM A, embedding A), (LLM B, embedding A),
(LLM A, embedding B), (LLM B, embedding B).

- Los documentos se vectorizan por modelo de embeddings y digest; el caché de
  vectores se separa por versión exacta del modelo. Esto evita reutilizar
  accidentalmente vectores de versiones distintas.
- Se recupera el mejor fragmento de cada documento y se ordenan documentos
  únicos por similitud coseno. El mismo `top_k` se usa en todas las condiciones.
- `Precision@k` = documentos relevantes recuperados / min(k, documentos del corpus).
- `Recall@k` = documentos relevantes recuperados / documentos relevantes
  etiquetados. `MRR` = recíproco del primer rango relevante.
- `Hit@k` = 1 si existe al menos un documento pertinente entre los primeros k.
- Para casos sin documentos pertinentes, estas métricas quedan nulas y se
  comprueba si el modelo devolvió el token `SIN_EVIDENCIA`.
- La verificación de citas solo confirma que los tokens `[F1]` corresponden
  a referencias enumeradas en el contexto; **no evalúa la verdad del texto**.
- La latencia medida por consulta comprende embedding de la pregunta,
  búsqueda y generación del modelo. La preparación del índice se informa aparte.
- Los errores se guardan por combinación y caso; no se sustituyen por ceros
  que podrían distorsionar promedios ni por resultados inventados.

## Reproducibilidad, integridad y límites

La ejecución guarda la huella del corpus, preguntas, etiquetas, nombres y
digests de los modelos, top-k, temperatura, respuestas y fuentes recuperadas.
Si el corpus cambia durante el experimento, la ejecución termina como fallida.

El motor utiliza un solo trabajo activo por proceso local y un hilo en segundo
plano. No sustituye Celery ni una cola tolerante a fallos: al reiniciar el
servidor, las tareas incompletas se marcan como interrumpidas. El experimento
real necesita Ollama y los cuatro modelos disponibles en el equipo.

**Pendiente para la validación científica:** incorporar un conjunto de al menos
veinte preguntas de fuentes reales, evaluar la fidelidad factual con una
revisora competente, contrastar consumo de RAM y p95 de latencia, y documentar
los resultados con incertidumbre y limitaciones. Ninguna prueba sintética es
una medición del dominio de ciencia de materiales.
