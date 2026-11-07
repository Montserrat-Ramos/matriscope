# Decisiones de arquitectura que necesitan evidencia

**Estado:** propuesta técnica. Ninguna de estas decisiones se declara validada
sin realizar los experimentos correspondientes.

| ADR | Decisión a contrastar | Datos necesarios |
| --- | --- | --- |
| 01 | Dos modelos de lenguaje locales y selección por complejidad | Exactitud, fidelidad a fuentes, latencia y memoria |
| 02 | Dos alternativas de embeddings | Acierto@k, idioma, espacio, tiempo de indexación |
| 03 | Umbral y TTL de caché semántica | Falsos positivos, ahorro de latencia e invalidación |
| 04 | Guardrails de entrada y salida | Casos bloqueados correctamente y falsos positivos |
| 05 | Tamaño y solapamiento de fragmentos | Acierto@k, costos y trazabilidad de páginas |
| 06 | Reformulación con máximo de iteraciones | Porcentaje de mejoras y costo adicional |

Para cada ADR final se deberá llenar: contexto, atributo de calidad, decisión,
alternativas, evidencia medida, consecuencias, responsables, estado y fecha.

