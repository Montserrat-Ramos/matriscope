# MatriScope · Fase 2: revisión científica y exportación trazable

## Propósito

Convertir el resultado de `POST /api/mapa-evidencia` en una unidad de trabajo
**persistente y revisable**. Ninguna afirmación se considera cierta simplemente
porque fue generada por un modelo de lenguaje o porque contiene una cita válida.

## Flujo implementado

1. El servicio RAG recupera los fragmentos de un proyecto, produce JSON y verifica
   que las referencias correspondan a los pasajes recuperados.
2. Cuando existe al menos una afirmación, se guarda un `analysis` con la pregunta,
   el resultado de extracción, su `trace_id` y la huella del corpus.
3. La pantalla **Validación científica** solicita todos los análisis del proyecto.
   Cada afirmación muestra su estado *pendiente*, las fuentes y el fragmento usado.
4. Una revisora declara su nombre, justifica la decisión y elige *aceptada*,
   *corregida* o *rechazada*. El servidor valida los campos y registra un evento
   en `claim_reviews` (inmutable desde la interfaz); nunca sobrescribe el historial.
5. El estado vigente de cada afirmación es su evento de revisión más reciente.
6. En **Informes**, la exportación se habilita si existe al menos una afirmación
   favorablemente revisada. Los pendientes y rechazados se excluyen del PDF.

## Contratos REST nuevos

| Método | Recurso | Función |
|---|---|---|
| `GET` | `/api/analisis?project_id=ID` | Lista análisis y resumen de revisión. |
| `GET` | `/api/analisis/ID` | Recupera una extracción y su historial. |
| `POST` | `/api/analisis/ID/revisiones` | Registra una decisión por afirmación. |
| `GET` | `/api/informes/ID.pdf` | Descarga informe revisado; rechaza si no hay aceptaciones. |

Ejemplo de decisión enviada a `POST /api/analisis/ID/revisiones`:

```json
{
  "indice": 0,
  "veredicto": "corregida",
  "revisor": "Nombre de quien revisa",
  "justificacion": "Explicación del cotejo contra la fuente original.",
  "texto_corregido": "Observación redactada con alcance acotado."
}
```

El `POST /api/mapa-evidencia` devuelve adicionalmente `analisis_id` al generar
afirmaciones guardables, o `null` si se abstiene o el mapa queda sin afirmaciones.

## Integridad científica y límites

- Los resultados de modelo se almacenan como propuestas, nunca como evidencias
  aceptadas de manera automática.
- Se conserva la salida original, incluso cuando la revisora modifica su redacción.
- La corrección no altera el fragmento científico ni la cita original; la persona
  revisora es responsable de justificar el sentido de la modificación.
- Se mantiene el historial de cambios en SQLite. El modelo de identidades es
  **declarativo, no autenticado**, por lo que no representa firma electrónica.
- El corpus puede cambiar: las extracciones anteriores exhiben la advertencia
  correspondiente. El PDF se bloquea si falta un documento citado.
- El informe declara el modelo, la traza, la pregunta, el estado de los ítems,
  las fuentes, páginas, DOI disponibles y las limitaciones metodológicas.
- Las pruebas de la aplicación usan documentos y respuestas **sintéticos** solo
  para validar software. Un resultado científico exige fuentes reales indexadas,
  revisión humana y evaluación con un conjunto etiquetado.

## Próximos criterios de calidad

- Autenticación local y roles de revisores; bloqueo por proyecto.
- Pruebas HTTP de extremo a extremo con modelos Ollama instalados.
- Comparación experimental reproducible entre al menos dos LLM y dos embeddings.
- Conjunto de evaluación científico con preguntas y respuestas de referencia.
- Mejorar exportación y portabilidad de citas bibliográficas; identificadores DOI
  deben cotejarse en origen, pues el sistema no los verifica automáticamente.
