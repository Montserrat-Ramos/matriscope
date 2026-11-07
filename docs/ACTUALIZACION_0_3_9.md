# MatriScope 0.3.9 — Comparación experimental trazable

## Motivo de esta actualización

En la prueba de la versión 0.3.8 se recuperaron cinco artículos sobre LPBF
316L, pero algunos pasajes seleccionados eran introducciones y no contenían
los valores experimentales disponibles en otras páginas. La matriz enumeraba
principalmente «Porosidad» y no distinguía valores medidos, recomendaciones ni
antecedentes citados.

## Cambios incluidos

1. **Selección experimental:** se favorecen pasajes con pares explícitos
   energía-densidad relativa, intervalos, porosidad y resultados numéricos.
   Se mantiene un pasaje destacado por documento para diversificar la búsqueda.
2. **Matriz enriquecida:** por documento se presentan variables, relaciones
   reconocidas, unidades, condiciones y métodos cuando aparecen en el texto.
   La página, la etiqueta [F#] y el fragmento permiten verificar cada dato.
3. **Distinción de procedencia:** valores reportados por otro estudio citado
   se señalan como antecedentes. Una energía recomendada sin porcentaje
   directamente vinculado no se presenta como una medición de densidad.
4. **Diferencias documentales:** se identifica qué artículos aportan intervalos,
   umbrales o métodos; se evita concluir que sus resultados son físicamente
   contradictorios sin comparar condiciones de fabricación y medición.
5. **Acceso al origen:** si el DOI fue cargado y tiene un formato válido,
   aparece un enlace al artículo. Los PDF originales no se almacenan ni se
   adjuntan automáticamente al resultado; conserva tus copias para revisar
   tablas, figuras y páginas.

## Actualización de Windows sin perder artículos

1. Detén el servidor con `Ctrl + C`.
2. **Respalda** el directorio `matriscope-app/data` de tu instalación actual.
3. Descomprime `MatriScope_v0.3.9_Comparacion_Experimental.zip`.
4. Copia los nuevos archivos del programa a tu instalación, conservando
   los existentes `data/`, `.env`, los PDF originales y tu configuración.
   **No reemplaces ni elimines la base SQLite del proyecto.**
5. Abre una terminal en `matriscope-app` y ejecuta:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

6. Comprueba la versión `0.3.9` en `http://127.0.0.1:8010/openapi.json`.
   Si la interfaz conserva una vista antigua, recarga con `Ctrl + F5`.

**No se requiere volver a indexar los cinco artículos.**

## Prueba de comparación recomendada

> Compara los resultados reportados por los diferentes artículos sobre la
> relación entre la densidad volumétrica de energía, la porosidad y la densidad
> relativa del acero inoxidable 316L fabricado mediante LPBF. Identifica
> coincidencias, diferencias, valores experimentales y las fuentes
> correspondientes.

### Qué verificar

- Al menos dos artículos distintos, de preferencia los cinco si aparecen
  entre los candidatos recuperados.
- `metals-11-00832-v3.pdf`: debe favorecerse la página que informa el intervalo
  de 45 a 125 J/mm³ y una densidad superior a 99.8 % si es recuperada.
- `materials-15-06672-v2.pdf`: debe favorecerse la relación explícita entre
  79/103 J/mm³ y 99.5/99.9 %, respectivamente, si aparece en el contexto.
- `jmmp-08-00035.pdf`: si recupera los porcentajes 99.41 % por Arquímedes y
  99.9 % por análisis de imágenes, debe distinguir ambos métodos; una
  recomendación de 125 J/mm³ no se debe afirmar como energía de ese resultado.
- Si un artículo cita un resultado previo de otro autor, debe marcarlo como
  antecedente y evitar presentarlo como medición del artículo que lo cita.
- La matriz debe declarar cuando no se detectó una relación cuantitativa
  explícita en un fragmento. Los resultados siguen `pendiente_revision`.

Pruebas de regresión: consultas por 99.9 % (103 J/mm³ con fuente directa)
y 99.7 % (abstención sin interpolar) deben mantener el comportamiento de 0.3.8.

## Alcance y limitaciones

La selección, extracción y matriz están basadas en patrones verificables del
texto y no invocan Ollama para la comparación. No se ha automatizado la
interpretación exhaustiva de tablas, figuras, PDF escaneados, incertidumbre
experimental o equivalencia de métodos entre publicaciones. El resultado es
una **matriz documental preliminar** que exige lectura y juicio científico.

## Verificación técnica

- 50 pruebas Python aprobadas, con una prueba HTTP omitida
  por no disponer de las dependencias FastAPI/HTTPX en este entorno.
- 4 pruebas Node.js de interfaz aprobadas.
- Pendiente: validación de extremo a extremo con el corpus y Ollama de Windows.
