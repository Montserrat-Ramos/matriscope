# MatriScope · Versión de desarrollo (0.3.21)

Plataforma científica local para organizar literatura autorizada, generar embeddings,
recuperar pasajes y construir afirmaciones **con citas y pendientes de revisión**.
El producto principal es el **Mapa de evidencia**, no un chatbot.

## Comparaciones estructuradas con Ollama (0.3.21)

- En comparaciones, el servicio solicita a Ollama **JSON estructurado**
  con afirmaciones, referencias explícitas y conclusión. El backend
  comprueba que el modelo haya declarado cada cita antes de presentarla
  al usuario; la validación numérica y de cobertura sigue activa.
- Cuando el PDF contiene un pasaje largo y una relación cuantitativa
  reconocible, el traductor procesa un **extracto pertinente** de hasta
  840 caracteres en lugar de encabezados, referencias y pies de página
  ajenos. La interfaz indica que es traducción abreviada y mantiene
  visible el fragmento original íntegro para comprobación.
- Los cambios conservan el modo `extractive`, la matriz de evidencia,
  la selección de `qwen2.5:3b` y los reintentos seguros.
- No es necesaria la reindexación de documentos ni una migración SQLite.

Consulta `docs/ACTUALIZACION_0_3_21.md`.

## Respuestas comparativas y tablas numéricas (0.3.20)

- En comparaciones de equivalencia con hechos explícitos de dos fuentes,
  se selecciona el pasaje más pertinente de **cada estudio** para evitar
  cinco traducciones redundantes y enviar menos ruido al modelo.
- Los fragmentos dominados por cifras provenientes de tablas o gráficas no
  se envían a Ollama para traducirlos como prosa. Se conserva el texto
  original y se muestra `contenido_tabular_no_traducible`; el PDF sigue
  siendo la referencia para revisar esos valores.
- Si una traducción altera cifras, las diferencias repetidas ahora se
  presentan con un contador (por ejemplo, `0.03 (7 veces)`) y sin listas
  largas de duplicados.
- Se normalizan variantes inequívocas de citas (`[F1, F2]` o `(F1)`).
  Si el modelo incluye un prólogo **sin citas** antes de afirmaciones
  fundamentadas, se conserva solo el texto que ya contiene referencias,
  y este debe superar **todos** los guardrails previos. No se agregan
  referencias inventadas ni se declara aprobada una respuesta sin sustento.
- Cuando la síntesis del modelo se rechaza, la interfaz muestra de todos
  modos el diagnóstico documental extractivo y la matriz de evidencia.
- No cambia SQLite, Ollama ni el índice de embeddings: **no requiere
  reindexar el corpus**.

Consulta `docs/ACTUALIZACION_0_3_20.md` para la actualización y pruebas.

## Razonamiento comparativo con Ollama (0.3.19)

- En una comparación científica, el modo `hybrid` ahora **ejecuta el modelo
  Ollama elegido** para contrastar resultados y justificar sus diferencias.
  Anteriormente devolvía inmediatamente una síntesis extractiva sin usar el LLM.
- Conserva junto a la respuesta razonada la **matriz de evidencia** y las
  fuentes PDF originales; `extractive` sigue disponible sin generación.
- El control comprueba que la respuesta cite por lo menos **dos artículos**,
  cubra todas las publicaciones nombradas, fundamente cada línea y preserve
  sus magnitudes. Para equivalencia/garantía, la conclusión debe citar ambos
  estudios. Esto **no acredita la verdad científica** de una interpretación:
  se mantiene el aviso de revisión humana.
- Si la generación falla los controles, se solicita una reparación al **mismo
  modelo seleccionado**. Si vuelve a fallar, se rechaza el texto del modelo
  y se muestra solo la comparación documental verificable, con diagnóstico.
- Los pasajes enviados al modelo se acortan alrededor de las relaciones
  científicas reconocidas; los fragmentos completos siguen disponibles.
- La selección de fuentes comparativas evita pasajes con resultados
  cuantitativos duplicados y da menos prioridad a tablas de composición
  química ajenas a la consulta.
- No cambia el esquema SQLite ni los embeddings: **no hay que reindexar**.

Consulta `docs/ACTUALIZACION_0_3_19.md` para los pasos de actualización.

## Comparaciones fundamentadas por publicación (0.3.18)

- Reconoce preguntas de equivalencia o garantía («¿Equivale ...?»,
  «¿Garantiza ...?») como **comparaciones**, incluso sin la palabra «compara».
- Identifica referencias a publicaciones por los nombres de los archivos
  indexados: por ejemplo `JMMP` y `Metals`. Cuando dos nombres se identifican,
  consulta sus fragmentos de forma separada antes de seleccionar las fuentes.
- Da prioridad a pasajes experimentales con las cifras y magnitudes mencionadas
  en la pregunta, respetando las relaciones **dentro de cada artículo**.
- Si una de las publicaciones citadas no tiene evidencia recuperable, se
  abstiene de responder y muestra **cobertura documental incompleta**.
- Para equivalencias numéricas exigidas entre dos estudios, requiere hechos
  documentales reconocibles en ambos y presenta un mensaje conservador:
  una recomendación de un artículo no garantiza resultados de otro.
- Si el texto extraído de un PDF incluye caracteres de control en una ecuación,
  **no la pasa al traductor**: reporta `ecuacion_pdf_no_interpretable` y
  conserva el original, evitando inventar símbolos matemáticos.
- Se preservan selección de modelos, `hybrid`, reintentos, traducciones,
  validación de citas y barras de progreso. **No se requiere reindexar PDF**.

Consulta `docs/ACTUALIZACION_0_3_18.md` para actualización y pruebas.

## Diagnósticos y reintentos verificables (0.3.17)

- El indicador global distingue **procesamiento de fuentes terminado** de
  **traducciones aprobadas**. Un 100 % de procesamiento puede incluir errores.
- Si una traducción falla por cambio de cifras o unidades, se identifican los
  valores **faltantes** y los **adicionales** en el texto rechazado.
- Se corrigió la comparación de porcentajes con y sin espacio (`0.38%` y
  `0,38 %`). También se comprueban los signos de valores negativos.
- En cada fuente fallida aparece **Reintentar con otro modelo** cuando esté
  disponible. El reintento procesa el pasaje con el modelo alternativo y
  muestra su nuevo progreso. No utiliza una traducción rechazada como válida.
- Se refuerzan las instrucciones de traducción y se bloquean expresiones
  incorrectas conocidas como «el key» o «cúmulos de estrés».
- El RAG conserva sus citas, revisión humana, filtro de alcance y modo `hybrid`.
- No se modifica la base de datos ni el corpus: **no se requiere reindexar**.

Consulta `docs/ACTUALIZACION_0_3_17.md` para actualización y comprobaciones.

## Barra de progreso y traducción científica protegida (0.3.16)

- Cada fuente muestra una **barra de progreso con porcentaje real** y cantidad
  de segmentos confirmados por Ollama (por ejemplo, 2 de 4 = 50 %).
- Una barra global resume cuántas fuentes han terminado; distingue traducciones
  correctas de fallos, sin ocultar el texto original.
- Mientras se procesa un segmento, el porcentaje puede permanecer en 0 % o en
  el valor anterior. **No representa tiempo transcurrido ni predice duración**.
- Se preservan cifras, unidades, referencias y algunas expresiones matemáticas
  mediante marcadores protegidos; el servidor los restaura y valida.
- Se admiten equivalencias técnicas del glosario, y se bloquean sustituciones
  incorrectas como «haz de lámpara» para *laser beam* o «molde de yeso»
  para *powder bed*. Si falla la traducción, aparece el diagnóstico y, si se
  dispone de ella, una vista previa del texto rechazado.
- Se conservan los selectores de `qwen2.5:3b` y `llama3.2:3b`, el modo
  `hybrid` y las validaciones de citas de las respuestas RAG.
- **Sin reindexación:** se mantienen la base SQLite y los PDF existentes.

Consulta `docs/ACTUALIZACION_0_3_16.md` para instalación y pruebas.

## Traducción técnica y control de modelos (0.3.15)

- Se añade un selector independiente de **modelo para traducir fuentes** en
  Explorador y Configuración. Por defecto sigue el modelo principal elegido;
  también puede fijarse `qwen2.5:3b`, `llama3.2:3b` u otro modelo instalado.
- En el resultado se distinguen **modelo seleccionado**, **modelo que respondió**,
  **modo de respuesta** y **modelo usado para traducir**. En `hybrid` es normal
  que el resultado use extracción directa sin invocar un LLM para responder.
- Los fragmentos extensos ahora se traducen en segmentos de aproximadamente
  340 caracteres, cada uno en una solicitud acotada; la pantalla informa el
  progreso de la traducción y continúa con la siguiente fuente.
- Si una traducción cambia cifras, unidades o vocabulario técnico crítico,
  se reintenta **una vez**, y después se conserva el original con un diagnóstico
  específico. Se incorpora un glosario de LPBF, VED, XCT, keyhole, balling,
  baños de fusión, falta de fusión y parámetros de escaneo.
- La memoria de traducciones se separa por proyecto, fragmento **y modelo**;
  la traducción de un modelo no sustituye la de otro.
- La validación sigue siendo conservadora, no garantiza que toda la terminología
  ni interpretación sea correcta. El texto inglés continúa siendo la fuente
  para una revisión científica formal.
- **Sin cambios de SQLite, corpus o embeddings: no se requiere reindexar PDF**.

Consulta `docs/ACTUALIZACION_0_3_15.md` para las pruebas de actualización.

## Selector de modelos Ollama y comparación directa (0.3.14)

- En **Explorador semántico** puedes elegir el LLM de Ollama y el modo
  `hybrid` (inicial), `generative` o `extractive`. El modelo inicialmente
  seleccionado es **`qwen2.5:3b`**; el alternativo es `llama3.2:3b`.
- **Híbrido:** conserva extracción directa para relaciones documentales
  verificables y usa generación solo cuando corresponde. Es normal que
  aparezca `Modelo: No utilizado` en respuestas puramente extractivas.
- **Generativo:** invoca el modelo elegido y mantiene los controles de citas,
  cifras y abstención. Los objetivos cuantitativos exactos documentados se
  preservan por extracción para no intercambiar valores y porcentajes.
- **Extractivo:** no llama al LLM para redactar. Si no detecta una relación
  reconocible en los pasajes, se abstiene.
- **Comparar modelos:** ejecuta dos modelos *secuencialmente* para la misma
  pregunta y los mismos documentos, **forzando el modo generativo** en ambas
  ramas. Muestra modelo realmente invocado, tiempo, estado, control de citas,
  fragmentos recuperados y traza; las respuestas siguen pendientes de
  comprobación humana.
- La API incorpora `GET /api/modelos`, `POST /api/comparar-modelos` y acepta
  `modelo`/`modo` en `POST /api/consultas` y `POST /api/mapa-evidencia`.
  Rechaza modelos no instalados sin sustituir silenciosamente el elegido.
- **No cambia SQLite, documentos originales ni embeddings**. No requiere
  reindexar los PDF ni borra los proyectos existentes. La traducción conserva
  su procesamiento progresivo por fragmento.

Consulta `docs/ACTUALIZACION_0_3_14.md` para instalar los modelos y probar
la comparación.

## Traducción progresiva y tiempos de espera controlados (0.3.13)

- Corrige el caso donde el explorador quedaba un minuto o más mostrando
  «Traduciendo fragmento al español…» para todos los pasajes. La versión 0.3.12
  enviaba hasta cinco fragmentos en un **único** trabajo de Ollama.
- Ahora envía **una fuente por solicitud**, primero las referencias citadas en
  la respuesta. El resto de los pasajes se traduce progresivamente.
- La traducción de cada fuente está acotada a 35 segundos en el servidor y
  40 segundos en la interfaz. Ante un error, se informa de forma visible y se
  conserva el texto original en inglés; no se mantiene una espera indefinida.
- Actualiza las traducciones sin desplazar la página hacia abajo cada vez y
  preserva los controles numéricos y la posibilidad de revisar el texto original.
- No cambia el esquema SQLite, la indexación de PDF ni el guardrail de
  consultas fuera del corpus. Conserva las mejoras científicas de 0.3.12.

Consulta `docs/ACTUALIZACION_0_3_13.md` para actualizar y repetir la prueba.

## Síntesis de energía y porosidad con pasajes en español (0.3.12)

- La consulta P03 sobre densidad volumétrica de energía y porosidad ya no se
  responde únicamente con umbrales de **densidad relativa**. Si las fuentes
  contienen relaciones explícitas, genera hasta dos afirmaciones diferenciadas:
  una tendencia dentro del estudio y los defectos que aparecen con energía
  insuficiente/excesiva. Conserva el artículo y la página de cada afirmación.
- La extracción se apoya en **patrones científicos delimitados**, no calcula
  resultados ni declara comportamientos universales. Si las relaciones no
  están explícitas, sigue el flujo normal de generación y abstención.
- Para preguntas sobre energía y porosidad, la recuperación da preferencia a
  los fragmentos que describen **mecanismos de defectos** y mantiene variedad
  entre artículos, sin alterar la prioridad de porcentajes objetivo (99.9 %).
- Los pasajes recuperados se traducen automáticamente al español por **Ollama
  local** en una solicitud posterior, sin frenar la respuesta inicial.
  **El texto original permanece disponible** para comparación y revisión.
- La traducción conserva cifras, unidades y ecuaciones: si el verificador
  detecta diferencias numéricas, se muestra el original. La equivalencia
  semántica de toda traducción sigue requiriendo verificación humana.
- Las traducciones se conservan en memoria durante la ejecución del servidor;
  no se modifica SQLite ni se requiere volver a indexar los documentos.

Consulta `docs/ACTUALIZACION_0_3_12.md` para pruebas y actualización.

## Alcance documental estricto (0.3.11)

- Antes de buscar fragmentos, un filtro decide si la solicitud pertenece al
  corpus del proyecto. Las operaciones aritméticas aisladas, por ejemplo
  «¿Cuánto es 2+2?», se rechazan sin invocar Ollama ni recuperar citas ajenas.
- Para consultas sin coincidencias con los metadatos del proyecto, el
  clasificador puede pedir a Ollama una decisión **DENTRO/FUERA/INCIERTO**
  usando nombres de documentos y muestras de los PDF ya indexados. Nunca le
  pide contestar la pregunta. La clasificación dudosa permite continuar con
  la búsqueda y con la abstención normal por falta de evidencias.
- El estado `fuera_de_alcance` no incorpora fragmentos ni una respuesta general,
  y la interfaz muestra «Consulta fuera del alcance» sin fuentes irrelevantes.
  Es diferente del estado «sin evidencia» para una pregunta pertinente.
- La regla se aplica también al mapa de evidencia. No modifica los datos,
  el esquema SQLite ni los documentos cargados; **no requiere reindexación**.
- Es un control conservador que debe validarse con preguntas de varios temas:
  puede haber falsos positivos o negativos al usar un modelo pequeño.

Consulta `docs/ACTUALIZACION_0_3_11.md` para los cambios y casos de prueba.

## Métodos experimentales y lectura clara de evidencias (0.3.10)

- La comparación reconoce **porosidad numérica por métodos diferenciados**.
  Por ejemplo, un pasaje que vincule mediante «respectively» los modelos
  óptico y XCT con 0.0009 % y 0.0003 % conserva ese orden y **no interpreta
  estos porcentajes como densidad relativa**. No asigna valores a métodos
  cuando el vínculo textual es ambiguo.
- Detecta relaciones cualitativas explícitas de contraste entre microscopía
  óptica y XCT según las condiciones del artículo. No generaliza esas
  observaciones a todas las máquinas o a todos los procesos LPBF.
- Amplía los patrones conservadores de extracción para intervalos de tamaño
  de poro (µm), dureza (HV), rugosidad (Ra/Rz) y parámetros de proceso.
  Estos valores se registran como propiedades independientes: no se mezclan
  con energía volumétrica ni densidad relativa.
- Cuando un artículo cita un valor ajeno de energía y porosidad, se identifica
  su procedencia y el equipo experimental si ambos están explícitos en el
  fragmento (por ejemplo, Renishaw AM 250).
- La matriz deja de introducir listas dentro de una tabla horizontal extensa:
  ahora presenta **una tarjeta por artículo**, con propiedades identificadas,
  hechos estructurados y el pasaje original desplegable. Se puede acceder
  al DOI cuando se declaró un identificador válido.
- El texto comparativo señala en cuáles fuentes hay resultados cuantitativos
  de porosidad o diferencias cualitativas entre métodos, dejando explícito
  que la comparación todavía requiere revisión científica.
- **Sin cambios de SQLite ni nueva indexación.** Conserva los proyectos,
  PDFs, datos y flujos de abstención fundamentada de versiones anteriores.

## Comparación experimental con procedencia (0.3.9)

- La búsqueda comparativa prioriza pasajes con **resultados cuantitativos
  explícitos** frente a introducciones y conserva la diversidad de artículos.
  Amplía el conjunto de candidatos revisados sin cambiar los embeddings.
- La matriz muestra por artículo **variables, valores energéticos, densidad
  relativa, porosidad, método y condiciones** cuando están explícitos.
  Ejemplos reconocidos: intervalos 45–125 J/mm³ con densidad >99.8 %, umbrales
  79/103 J/mm³ asociados respectivamente a 99.5/99.9 % y porcentajes de
  densificación calculados mediante métodos diferentes.
- Distingue resultados del artículo, **antecedentes científicos citados por
  sus autores** y recomendaciones energéticas sin porcentaje asociado.
  Una recomendación de 125 J/mm³ nunca se convierte por proximidad en una
  densidad de 99.9 % medida en otra oración.
- Resume coincidencias *temáticas* y diferencias en el **tipo de evidencia
  reportada**, no diferencias físicas entre estudios que no hayan sido
  metodológicamente contrastados. Todas las filas incluyen documento, página
  y pasaje original. Cuando se declaró un DOI válido, ofrece enlace al artículo.
- La extracción utiliza patrones deliberadamente limitados; si el pasaje no
  contiene una relación reconocible lo indica. No calcula nuevas propiedades,
  no interpreta imágenes o tablas automáticamente y **no certifica resultados**.
- Se mantienen los proyectos, la base SQLite, las APIs y la indexación previa.
  La huella de versión invalida respuestas antiguas en caché; no se requiere
  migración ni reindexación de los PDF.

## Abstención fundamentada y comparación de estudios (0.3.8)

- Si se solicita un porcentaje **específico de densidad relativa** y no aparece
  una relación energética explícita en los fragmentos seleccionados, el
  Explorador se **abstiene** sin extrapolar ni interpolar. La prueba del 99.7 %
  ya no transforma el umbral del 99.5 % en una garantía para el 99.7 %.
- Las preguntas de comparación buscan fragmentos de **documentos distintos**
  y presentan una matriz documental con variables, pasajes originales y
  referencias. Si hay menos de dos documentos, se informa que falta evidencia.
  La matriz es un análisis preliminar, no una comparación experimental validada.
- Las respuestas generadas por un LLM no se guardan en caché de consultas:
  una referencia formalmente válida no demuestra fidelidad factual. Se cambia
  la revisión del contexto para evitar reutilizar respuestas anteriores.
- Un nuevo filtro identifica magnitudes numéricas con porcentaje, J/mm³, HV o
  µm en texto generativo y comprueba que aparezcan con el mismo valor y unidad
  en la fuente citada. **No prueba causalidad ni equivalencia metodológica**.
- El Explorador muestra el contador de generación incluso cuando es cero y
  presenta una tabla de evidencia para preguntas comparativas. Toda revisión
  científica continúa siendo responsabilidad del usuario.
- Los endpoints y el esquema SQLite se mantienen; no hay migración y **no
  es necesario volver a indexar los PDF**.

## Preguntas por densidad relativa específica (0.3.7)

- Se corrige la regresión observada al preguntar por el valor energético
  correspondiente a una densidad relativa concreta (por ejemplo, 99.9 %).
  El valor buscado se extrae de una relación explícita en **un mismo pasaje**;
  no se vinculan cifras procedentes de artículos o páginas diferentes.
- La selección de fragmentos prioriza el **porcentaje exacto solicitado**.
  Un intervalo asociado al 99.8 % ya no desplaza el umbral explícito del
  99.9 % si ambos están presentes entre los candidatos recuperados.
- Para pares de porcentajes y energías vinculados por "respectively", el
  sistema preserva el orden de asociación. También reconoce una asociación
  singular directa entre energía y densidad relativa.
- Cuando encuentra el par específico, construye una respuesta extractiva
  con cita y página **antes de invocar al modelo de lenguaje**. El campo
  `intentos_generacion` es `0` y el modelo figura como no utilizado.
- Si no encuentra una asociación textual suficientemente clara, no infiere
  correspondencias. Para esa pregunta tampoco sustituye una negativa del
  modelo por intervalos genéricos que no respondan al porcentaje requerido.
- No cambia SQLite, los endpoints ni los documentos indexados. La nueva
  revisión del contexto invalida respuestas en caché de versiones previas.

La identificación de pares numéricos es un apoyo a la revisión documental,
no una validación experimental ni una solución universal para cualquier
redacción de los artículos. Las respuestas siguen pendientes de revisión.

## Respaldo extractivo cuantitativo (0.3.6)

- Si una respuesta generada no supera la validación de citas, el Explorador
  puede construir una **síntesis extractiva** cuando los pasajes contienen
  relaciones cuantitativas explícitas y estructuradas entre energía y densidad.
- Reconoce patrones limitados de intervalos de energía asociados a porcentajes
  de densidad y pares de umbrales que los autores presentan respectivamente.
  **No empareja porcentajes por proximidad ni mezcla artículos distintos**.
- La salida presenta las cifras con las etiquetas de los fragmentos que las
  contienen y los documentos/páginas correspondientes. No añade citas al texto
  rechazado de Ollama: genera otra respuesta desde los pasajes originales.
- Cuando la evidencia encaja en estos patrones, evita un segundo intento de
  generación fallido. Para otras preguntas, se conserva el reintento y la
  abstención segura de la versión anterior.
- La interfaz identifica expresamente cuándo se mostró una respuesta
  extractiva. El contenido sigue **pendiente de revisión humana**, no se
  considera una conclusión validada ni se guarda como respuesta de caché.
- Esta versión no altera la base SQLite ni requiere reindexar los artículos.

La extracción tiene un alcance deliberadamente limitado: no reconoce todas
las formas de redactar resultados científicos ni sustituye una interpretación
experta de tablas, metodologías y figuras. Si no puede establecer una relación
textual clara, el sistema mantiene su mecanismo de abstención.

## Formato de citas y evidencia de respaldo (0.3.5)

- El Explorador pide de dos a cuatro afirmaciones breves, cada una con citas
  asociadas al dato y no únicamente al final de la respuesta.
- Se normalizan variantes tipográficas inequívocas como `[f 1]` → `[F1]`.
  Una fuente inexistente, como `[F99]` cuando no se recuperó, sigue siendo rechazada.
- Ante un fallo de validación se hace **un solo reintento** con el motivo de rechazo.
  Si tampoco es verificable, no se atribuyen citas arbitrarias al texto generado.
- El respaldo presenta extractos de los documentos seleccionados alrededor de
  los resultados relevantes. Para energía y densidad intenta mostrar primero
  artículos diferentes; conserva los fragmentos originales para revisión.
- La interfaz distingue número de búsquedas e intentos de generación, y muestra
  el motivo de validación que provocó el respaldo. Esto facilita diagnosticar
  tiempos largos causados por un segundo intento.
- La revisión del prompt invalida la caché previa. **No requiere migración
  SQLite ni volver a indexar los PDF**. Se mantienen las rutas de la API.

La extracción documental sigue siendo evidencia pendiente de revisión humana:
la nueva versión no convierte automáticamente los extractos en conclusiones
científicas certificadas.

## Fidelidad de afirmaciones y recuperación cuantitativa (0.3.4)

- Se corrige el caso observado en la prueba con artículos de 316L: la respuesta
  no puede negar que existen resultados cuantitativos y acto seguido repetir
  las mismas cifras como si no fueran valores directos.
- Los controles exigen al menos una cita en el cuerpo de la síntesis, no solo
  en el apartado final de referencias; los párrafos científicos extensos
  también necesitan una fuente. Si el modelo falla, se reintenta una vez y
  después se muestran pasajes originales para revisión.
- Para preguntas que combinan **energía y densidad**, se reordenan los pasajes
  recuperados dando preferencia a los que describen ambas magnitudes con sus
  unidades (J/mm³ y porcentaje), conservando el umbral de similitud configurado.
  Se priorizan páginas distintas para no ocupar el contexto con repeticiones.
- La comprobación de contradicciones solo considera resultados de densidad:
  no toma porcentajes de composición química como medidas de densidad relativa.
- Se refuerza el prompt para distinguir porosidad, tamaño de poro, dureza y
  densidad relativa. El modelo puede continuar equivocándose; las citas y
  afirmaciones **siguen pendientes de revisión humana**.
- La huella de caché cambia para no reutilizar las síntesis generadas antes
  de esta actualización. No se requiere volver a indexar el corpus ni migrar SQLite.

En el ejemplo del corpus, el artículo de *Metals* 2021 informa el intervalo
45–125 J/mm³ con densidades superiores al 99.8 % (análisis de imágenes).
El artículo de *Materials* 2022 comunica umbrales de 79 y 103 J/mm³ para
99.5 % y 99.9 % de densidad relativa, respectivamente. Estos datos deben
comprobarse en el texto y la metodología originales; no se precargan como
respuestas en el sistema.

## Corrección de citas en Explorador semántico (0.3.3)

- Si el modelo devuelve una respuesta sin citas `[F1]`, `[F2]`, etc. válidas,
  se realiza **un único reintento** con instrucciones de referencia más explícitas.
- Si tampoco devuelve citas verificables, se **descarta la síntesis** y se
  muestran hasta tres pasajes originales, con archivo, página y referencia.
  No se agregan citas artificialmente a conclusiones no comprobadas.
- La vista deja de mostrar un error HTTP de validación para este caso recuperable;
  sigue indicando que los resultados necesitan revisión humana.
- Las respuestas sustituidas por fragmentos no se guardan en la caché de respuestas:
  otra consulta puede intentar generar una síntesis nuevamente.
- Se actualiza la versión del prompt para invalidar respuestas antiguas en caché.
  No se modifica el esquema de datos ni los endpoints existentes.

La recuperación alternativa **no certifica** la pertinencia científica de cada
fragmento; es una forma transparente de mostrar la evidencia disponible mientras
la síntesis del modelo necesita revisión.

## Mejora de precisión científica en 0.3.2

- El prompt exige comprobar las cifras y unidades de los fragmentos antes de
  concluir que una publicación no informa resultados cuantitativos.
- Un control de coherencia identifica un caso delimitado: respuestas que niegan
  valores sobre densidad de energía y densidad relativa cuando los fragmentos
  recuperados contienen simultáneamente valores en J/mm³ y porcentajes.
  En tal caso, **descarta la respuesta contradictoria** y muestra extractos
  originales con número de página y etiqueta de fuente para revisión humana.
- La regla no deduce resultados nuevos, ni valida automáticamente las figuras,
  métodos o causalidad de los artículos. Otros errores de razonamiento siguen
  siendo posibles y requieren revisión por la investigadora.
- Se cambia la revisión del prompt en la clave de caché para no reutilizar
  respuestas previas a esta mejora.
- Incluye pruebas de regresión para el caso de 316L con un intervalo reportado
  de 45–125 J/mm³ y densidad superior al 99.8 %, y para evitar falsos positivos.
- No hay migraciones SQLite ni cambios de contratos HTTP.

**Para actualizar una instalación existente:** detén el servidor; sustituye
los archivos del programa por esta versión, **conservando tu carpeta `data/`,
el archivo `.env` si lo tienes y tus PDFs propios**. Reinicia Uvicorn.
Los documentos ya indexados y los proyectos se conservan en SQLite.

## Mejoras de interfaz en 0.3.1

- Las operaciones que esperan una respuesta de la API (cargar e indexar PDF,
  consultar el corpus, construir mapas, guardar revisiones y ejecutar evaluaciones)
  bloquean clics repetidos hasta finalizar.
- Cuando la solicitud tarda, aparece una pantalla de carga con el nombre de la
  operación y el tiempo transcurrido. La barra animada **no** representa un
  porcentaje de avance real; evita transmitir un progreso ficticio.
- El Explorador semántico permite preguntas más extensas, tres ejemplos
  reutilizables, limpieza del campo y envío con **Ctrl + Enter** (o Cmd + Enter).
- Los mensajes de error del backend siguen mostrándose y la interfaz se libera
  al terminar, tanto si la operación tiene éxito como si falla.
- Esta actualización no cambia los esquemas SQLite ni los contratos de la API.

Pruebas adicionales de la interfaz (con Node.js instalado):

```powershell
node --test tests/test_web_ui.cjs
```

## Estado real de implementación

**Incluido en el código:**

- Web con diseño MatriScope y conexión HTTP a proyectos, carga documental, consultas,
  mapa de evidencia, comentarios y métricas.
- API REST FastAPI y documentación OpenAPI automática en `/docs`.
- C1 API; C2 orquestación con hasta dos iteraciones; C3 verificaciones de entrada y salida;
  C4 caché exacta y semántica; C5 extracción/fragmentación y RAG; C6 enrutador y gateway
  con respaldo; C7 adaptador Ollama y almacenamiento SQLite.
- T1 trazas de consultas y métricas registradas; T2 opinión útil/no útil ligada a traza.
- Ingesta PDF con texto, Markdown y TXT, páginas fuente, hashes SHA-256, embeddings reales
  generados por Ollama y almacenados con los fragmentos.
- Mapas de evidencia persistidos en SQLite con vínculo al proyecto, corpus y traza del RAG.
- Revisión humana por afirmación: aceptar, corregir o rechazar con revisor y justificación.
  Cada decisión queda en un historial de eventos que no se sobrescribe.
- Exportación PDF solo con afirmaciones aceptadas o corregidas; se incluyen fragmentos,
  documentos, páginas, DOI cuando exista y limitaciones de interpretación.
- Pantallas **Validación científica** e **Informes** conectadas a la API y a los datos
  efectivamente registrados, sin conclusiones científicas simuladas.
- **Evaluación experimental**: registro persistente de preguntas etiquetadas por una
  persona, selección de documentos pertinentes o ausencia de evidencia, y activación
  o desactivación de casos sin borrar su historial.
- Ejecutor local en segundo plano para las **cuatro combinaciones** de dos modelos
  de lenguaje y dos embeddings. Registra progreso, configuración, digest de modelos,
  huella del corpus, respuesta, fuentes recuperadas, duración y errores.
- Métricas de recuperación por documento (`Precision@k`, `Recall@k`, `MRR`, `Hit@k`),
  abstenciones de casos negativos, comprobación formal de citas y latencia media.
- Interfaz del nuevo módulo con ficha de casos, historial, tablas comparativas,
  gráfica de Recall@k, resultados por pregunta, CSV y progreso de ejecución.

**Aún por desarrollar o validar:**

- **Realizar** la comparación con Ollama y el corpus científico autorizado: el
  ejecutor existe, pero no hay resultados experimentales reales precargados.
- Construir y revisar un conjunto de al menos veinte casos científicos auténticos;
  ampliar las pruebas de robustez y casos adversariales.
- Diagramas/ADR definitivos y pruebas de extremo a extremo con Ollama real.
- Autenticación, permisos multiusuario, límite de uso robusto, OCR de PDF escaneados, adaptador Chroma
  (el índice vectorial inicial usa SQLite + similitud coseno) y panel de métricas por etapa.
- Calibración de umbrales, medición de recursos y verificación de latencia por capa.
- Juicio experto de fidelidad factual de las respuestas: se requiere evaluación
  humana; una cita formalmente correcta no prueba que la conclusión sea verdadera.

## Requisitos de ejecución en Windows 11

- Python 3.11 o 3.12.
- [Ollama](https://ollama.com/) instalado y ejecutándose **localmente**.
- RAM suficiente para los modelos elegidos; la viabilidad se determina mediante pruebas en el equipo.

En PowerShell, desde la carpeta `matriscope-app`:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

En otra terminal instala y activa los modelos candidatos:

```powershell
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
ollama pull bge-m3
ollama list
```

Los cuatro modelos son **candidatos**, no seleccionados definitivamente. El primero de
embeddings es el activo de esta versión y el segundo se reserva para comparación experimental.

Inicia el servicio desde la carpeta del proyecto:

```powershell
python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Abre:

- Interfaz: <http://127.0.0.1:8000>
- Documentación OpenAPI: <http://127.0.0.1:8000/docs>
- Salud de servicios: <http://127.0.0.1:8000/api/health>

> No publicar este servidor en internet: está orientado a ejecución local individual y todavía no
> tiene autenticación ni aislamiento multiusuario.

## Flujo funcional

1. Crea un proyecto de investigación en **Proyectos**.
2. Selecciona un PDF con texto y permiso de uso comprobado en **Biblioteca científica**.
   El archivo se indexa y se guardan fragmentos con número de página.
3. En **Explorador semántico**, consulta los pasajes del corpus con su referencia.
4. Desde **Mapa de evidencia**, formula la pregunta científica y revisa las afirmaciones y fuentes.
5. En **Validación científica**, examina cada fuente y registra aceptar, corregir o
   descartar con nombre del revisor, texto corregido cuando aplique y justificación.
6. En **Informes**, descarga el PDF del análisis cuando exista al menos una afirmación
   aceptada o corregida. El informe no incluye afirmaciones pendientes ni descartadas.
7. Califica la utilidad de la respuesta; la opinión se une al identificador de la traza.
8. Consulta en **Operación y métricas** los registros obtenidos en ejecución.
9. Abre **Evaluación experimental**, crea casos con preguntas y documentos
   realmente relevantes; incluye también preguntas cuya respuesta sea inexistente
   en el corpus. Activa la comparación **2 × 2** y consulta resultados y errores.

**Importante:** la primera evaluación puede tardar bastante porque requiere
calcular vectores para cada modelo de embeddings. Ejecuta un experimento piloto
antes de cargar el conjunto definitivo. Cada ejecución congela los casos y la
configuración; los resultados se almacenan en SQLite y sobreviven al reinicio.
Al reiniciar el servicio se marcarán como interrumpidas las ejecuciones que
seguían en proceso (no existe un sistema externo de colas en esta versión).

Si Ollama no está disponible, no hay índice o la salida no tiene citas verificables,
el sistema reporta un error o se abstiene. No produce un análisis inventado.

## Organización

```text
web/                       Presentación (nunca llama directamente a modelos)
servicio/api/              C1 · API REST y contratos
servicio/orquestacion/     C2 · Flujo y ciclo de agente
servicio/guardrails/       C3 · Validación de entrada y salida
servicio/cache/            C4 · Caché exacta/semántica
servicio/contexto/         C5 · Ingesta y RAG
servicio/modelos/          C6 · Selección/gateway/fallback
servicio/datos/            C7 · SQLite/Ollama
servicio/observabilidad/   T1 · Trazas y métricas
servicio/retroalimentacion/T2 · Opinión ligada a una traza
servicio/informes/         PDF basado en afirmaciones revisadas y fuentes
servicio/evaluacion/       Experimentación 2 × 2 y métricas reproducibles
tests/                     Pruebas automatizadas locales
evaluacion/                Criterios de preparación del conjunto de referencia
docs/                      Decisiones y diagramas de arquitectura
```

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas centrales usan dobles de modelo y **no** sustituyen la demostración con
Ollama real. Las salidas de prueba son sintéticas y están limitadas al ámbito de test.

## Seguridad, licencias y límites

- Solo se deben indexar documentos cuyo uso esté permitido; la licencia es declarada
  por quien sube el archivo y **no se valida legalmente de forma automática**.
- No subas datos personales ni sensibles.
- Los modelos pueden equivocarse. Cada afirmación necesita revisión del artículo original.
- Los nombres de quienes revisan se capturan como **declaraciones manuales**; todavía
  no hay inicio de sesión ni verificación criptográfica de identidad. No usar para
  expedientes regulados ni como certificación de investigación.
- Si un documento de origen se elimina, la API impide exportar informes que lo citen.
- La comparación usa ejecución directa y sin caché de respuestas para evitar
  contaminar la medición. No mide automáticamente la verdad factual de las frases.
- No ejecuta múltiples experimentos a la vez en el mismo proceso local. El servidor
  debe utilizar un solo worker; no es una cola distribuida de trabajos.
- Si el corpus cambia entre la extracción y la exportación, la interfaz y el PDF
  advierten que es necesario volver a revisar la vigencia de las fuentes.
- Los PDF escaneados sin texto no se procesan en esta versión: es necesario OCR verificable.
- El contenido de documentos no se ejecuta como instrucciones del modelo, pero la defensa
  ante inyección no está exhaustivamente validada: conserva el uso académico local.

## Fuentes del diseño académico

- `Proyecto_integrador_RAG.pdf`, secciones 3–12 (material de la asignatura).
- `Rubrica_proyecto_integrador_RAG.pdf`, requisitos R1–R12 y capas C1–C7/T1–T2.
- [Documentación oficial de FastAPI](https://fastapi.tiangolo.com/).
- [Documentación oficial de Ollama](https://docs.ollama.com/api/).

