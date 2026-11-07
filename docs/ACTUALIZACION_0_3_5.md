# Actualizar MatriScope de 0.3.4 a 0.3.5

Esta actualización mejora las citas en el Explorador semántico y muestra
evidencia cuantitativa más pertinente cuando el modelo no logra una síntesis
con referencias verificables.

## Pasos en Windows

1. Detén Uvicorn con `Ctrl + C`.
2. Haz una copia de seguridad de la carpeta `matriscope-app/data` de tu instalación.
3. Descomprime `MatriScope_v0.3.5_Citas_y_Evidencia.zip` en otra ubicación.
4. Copia los archivos del programa de la carpeta `matriscope-app` nueva a la
   carpeta de tu instalación. **Conserva los archivos de tu instalación**
   que no están en el paquete, especialmente `data/`, `.env`, PDF propios y
   configuraciones locales. No sustituyas ni borres la base SQLite.
5. Reinicia el backend desde tu carpeta `matriscope-app`:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

6. Comprueba la versión `0.3.5` en `http://127.0.0.1:8010/openapi.json`
   y el estado de modelos en `http://127.0.0.1:8010/api/health`.
7. En Explorador semántico, vuelve a ejecutar la pregunta sobre densidad
   volumétrica de energía y densidad relativa del acero 316L. Revisa
   **Intentos de generación**, **Diagnóstico de validación** y las fuentes.

No es necesario volver a cargar ni indexar los cinco documentos.

## Qué significa cada resultado

- **Respuesta con citas:** el formato de las referencias pasó la validación
  automática; la exactitud científica aún necesita revisión humana.
- **Respuesta con citas tras reintento:** el primer texto falló la validación,
  pero el segundo cumplió el formato requerido.
- **Respaldo documental:** ambos intentos fallaron; MatriScope descartó la
  síntesis del modelo y presenta fragmentos originales. Esto evita atribuir
  al modelo conclusiones no demostradas, aunque no equivale a una síntesis.

## Verificación automatizada realizada

- 33 pruebas de lógica Python aprobadas (la prueba HTTP requiere FastAPI y
  HTTPX instalados en el entorno de pruebas).
- 3 pruebas de interfaz Node.js aprobadas.
- El comportamiento con Ollama instalado en tu equipo debe comprobarse
  manualmente: el paquete no incluye modelos ni archivos de investigación.
