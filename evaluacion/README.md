# Evaluación experimental (motor implementado; corpus real pendiente)

Los casos etiquetados y resultados de cada ejecución ahora se almacenan en SQLite,
mediante el módulo **Evaluación experimental** de la interfaz. Esta carpeta
documenta el protocolo y los criterios de calidad, sin resultados científicos
precargados. Las pruebas sintéticas están aisladas en `tests/`.

Conjuntos requeridos por el enunciado:

1. Un mínimo de 20 preguntas o solicitudes científicas con respuesta esperada y fuente.
2. Al menos 10 solicitudes problemáticas y 10 normales para guardrails.
3. Consultas exactas y paráfrasis para la caché.
4. Consultas clasificadas por complejidad para validar el enrutador.
5. Casos de recuperación inicial deficiente para evaluar el ciclo del agente.

Los valores provisionales de `min_similarity`, `cache_similarity`, tamaño de fragmento
y selección de modelos deberán calibrarse a partir de esos casos y documentarse en ADR.

## Protocolo de la comparación 2 × 2

1. Definir la pregunta y etiquetar manualmente uno o varios documentos pertinentes
   del proyecto, o declarar que no hay evidencia suficiente en el corpus.
2. Ejecutar una misma colección de casos con dos modelos de lenguaje y dos
   modelos de embeddings instalados en Ollama.
3. Emplear exactamente el mismo top-k, prompt, temperatura y colección de
   documentos en las cuatro combinaciones; se deshabilita la caché de respuestas.
4. Comparar ranking de **documentos distintos**, no cantidad de fragmentos del
   mismo PDF. Se registran P@k, Recall@k, MRR y Hit@k.
5. Registrar tiempos de consulta y preparación de embeddings, abstenciones
   declaradas y referencias con sintaxis formal válida.
6. Mantener por separado la **evaluación humana de fidelidad científica**:
   la sintaxis de una cita no demuestra que su interpretación sea correcta.
7. Interpretar resultados solo cuando haya suficientes casos genuinos, y mostrar
   tamaño de muestra y posibles sesgos (longitud documental, idioma, condiciones).

## Límites

En esta versión, la diferencia de LLM se refleja en respuestas, formato de citas,
abstenciones y latencia. Las métricas de recuperación son principalmente función
del embedding: no interpretarlas como medidas independientes de los LLM.

Los casos *sin evidencia* no contribuyen a las métricas de ranking positivo;
evalúan el cumplimiento de la abstención. Los casos que producen error se cuentan
pero no se incluyen en promedios de ejecuciones exitosas.

