# Arquitectura implementada — MatriScope 0.1

Documento de código, no informe de resultados. Se describe la **primera fase** y sus límites.

## Contenedores y dependencias

```mermaid
flowchart TB
    Investigador[Investigadora] --> Web[Presentación web]
    Web --> API[C1 API REST]
    API --> Orq[C2 Orquestación]
    Orq --> Guarda[C3 Guardrails]
    Orq --> Cache[C4 Caché]
    Orq --> Contexto[C5 RAG y contexto]
    Orq --> Gateway[C6 Router y gateway]
    Contexto --> Datos[C7 Adaptadores]
    Gateway --> Datos
    Datos --> Ollama[Ollama local]
    Datos --> SQLite[SQLite local y vectores]
    Orq --> Obs[T1 Trazas]
    Web --> Feedback[T2 Feedback vía API]
    Feedback --> SQLite
```

La aplicación web se comunica **exclusivamente** con C1 mediante HTTP. Los modelos
no son accesibles directamente desde el navegador. La presentación y el servicio
corren en el mismo origen HTTP para esta versión local.

## Secuencia ejecutable: consulta RAG

```mermaid
sequenceDiagram
    actor U as Investigadora
    participant W as Web
    participant A as C1 API
    participant O as C2 Orquestación
    participant S as C3/C4/C5/C6
    participant D as C7 Ollama/SQLite
    U->>W: Pregunta científica
    W->>A: POST /api/consultas
    A->>O: analyze(proyecto, pregunta)
    O->>S: Verificar entrada y caché
    alt Caché válida
      S-->>O: Respuesta almacenada
    else Sin acierto
      O->>D: Embedding de consulta
      O->>S: Recuperar contexto
      S->>D: Leer fragmentos/vector
      D-->>S: Pasajes y páginas
      O->>S: Enrutar y generar
      S->>D: Chat local en Ollama
      D-->>S: Respuesta
      O->>S: Comprobar citas
    end
    O-->>A: Resultado + fuentes + traza
    A-->>W: JSON
    W-->>U: Evidencias para revisión
```

## Decisiones y controles de la fase

- **C1:** validación de datos JSON/Form y códigos HTTP de error.
- **C2:** reformulación conservadora con número máximo de iteraciones.
- **C3:** validación de longitud/caracteres e intentos explícitos de alterar
  instrucciones; salida con esquema y referencias válidas. Esto no constituye
  un control exhaustivo de seguridad.
- **C4:** caché exacta y semántica con expiración. La huella de corpus y los
  parámetros principales se incluyen para evitar reutilización indebida.
- **C5:** fragmentación que conserva número de página y recuperación por coseno.
- **C6:** ruta inicial por tipo de operación con modelo de respaldo.
- **C7:** adaptadores locales para Ollama y SQLite; aún falta un motor vectorial
  optimizado para escalabilidad.
- **T1/T2:** traza por consulta, métricas agregadas, opinión útil/no útil.

## Elementos que no se deben presentar como terminados

Selección experimental de modelos, calibración de umbrales, evaluación de corpus,
latencia por capa, revisión humana persistida por afirmación, exportación
científica y diagramas de secuencia correspondientes a caché, bloqueo,
ingesta y ciclo de agente aún necesitan pruebas y desarrollo adicional.

