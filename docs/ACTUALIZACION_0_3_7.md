# MatriScope 0.3.7 — Respuestas a valores cuantitativos específicos

Esta versión corrige el caso observado al preguntar por la energía necesaria
para alcanzar una densidad relativa del 99.9 % en acero inoxidable 316L.

## Qué cambia

- Identifica el porcentaje de **densidad relativa** que se busca.
- Prioriza fragmentos donde ese porcentaje aparece relacionado con la energía.
- Detecta pares de resultados expresamente asociados en el mismo pasaje.
- Si la evidencia es inequívoca, presenta el valor energético y su cita sin
  pedir una redacción al LLM. No mezcla cifras de diferentes documentos.
- Si no hay asociación textual clara, no inventa una correspondencia.

Con el fragmento de *Materials* 2022 recuperado en la prueba, la consulta por
99.9 % debe producir **103 J/mm³**, y la consulta por 99.5 % debe producir
**79 J/mm³**, con la página documental correspondiente a cada fuente.

**Importante:** no se han precargado estos números como una tabla fija: son
valores que deben aparecer en los fragmentos recuperados. La extracción
reconoce patrones limitados de redacción científica y los resultados siguen
pendientes de revisión en el documento original.

## Instalar conservando los documentos

1. Detén el servidor de MatriScope con `Ctrl + C`.
2. Haz una copia de seguridad de tu carpeta `matriscope-app/data`.
3. Descomprime `MatriScope_v0.3.7_Consulta_Cuantitativa.zip`.
4. Actualiza los archivos del programa **sin borrar ni sustituir** tu
   carpeta `data/`, `.env` ni tus documentos originales.
5. En PowerShell, dentro de la carpeta instalada, reinicia:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

6. Verifica la versión en `http://127.0.0.1:8010/openapi.json` y el servicio
   en `http://127.0.0.1:8010/api/health`.
7. Prueba la pregunta exacta:

   > ¿Qué valor de densidad volumétrica de energía se reporta para alcanzar
   > una densidad relativa del 99.9 % en el acero inoxidable 316L?
   > Indica el documento y la página.

8. Comprueba que los datos provengan de `materials-15-06672-v2.pdf` y que la
   referencia corresponda a la página recuperada; esta puede variar según
   el fragmento indexado. La respuesta directa mostrará cero intentos de
   generación cuando el patrón textual sea reconocido.

**No necesitas volver a indexar los cinco artículos.**

## Pruebas automatizadas

- 40 pruebas Python aprobadas; una prueba HTTP omitida por dependencias
  faltantes en el entorno de verificación.
- 3 pruebas de interfaz aprobadas.
- La prueba con Ollama real y tu corpus local debe realizarse en tu equipo.
