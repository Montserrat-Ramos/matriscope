# Actualización de MatriScope a la versión 0.3.6

La prueba de la versión 0.3.5 mostró que `llama3.2:3b` continuaba
omitiendo las referencias de los documentos incluso tras un reintento. Aunque
la recuperación de pasajes era correcta, el usuario seguía recibiendo solo
los fragmentos originales.

## Mejora incorporada

Para consultas sobre **densidad de energía y densidad relativa**, cuando
la respuesta del modelo no contiene citas válidas, MatriScope ahora intenta
extraer relaciones numéricas explícitas de los pasajes originales.

Ejemplo de una extracción admisible si el propio documento contiene todos
los valores en el mismo pasaje:

- Intervalo de 45 a 125 J/mm³ y densidades superiores al 99.8 %.
- Mínimos de 79 y 103 J/mm³ para densidades relativas de 99.5 % y 99.9 %,
  respectivamente.

Los valores no están precargados como respuestas; solo pueden aparecer si
los patrones y cifras se encuentran en el corpus recuperado. Este mecanismo
no acepta comparaciones que requieran inferir resultados ausentes ni convierte
la salida en una afirmación científica automáticamente aprobada.

## Instalar en Windows 11

1. Detén Uvicorn con `Ctrl + C`.
2. Haz una copia de seguridad de tu carpeta `matriscope-app/data`.
3. Descomprime `MatriScope_v0.3.6_Respaldo_Extractivo.zip`.
4. Copia los archivos del programa sobre tu instalación anterior,
   **conservando `data/`, `.env`, los PDF propios y configuraciones locales**.
   No borres ni sustituyas tu base SQLite.
5. Desde la carpeta de la aplicación ejecuta:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

6. Comprueba `http://127.0.0.1:8010/openapi.json` (versión `0.3.6`) y
   `http://127.0.0.1:8010/api/health` (servicios locales).
7. Vuelve a consultar la relación entre densidad volumétrica de energía y
   densidad relativa de 316L en el Explorador semántico.

En el resultado puedes encontrar la indicación **Resultado extractivo**.
Significa que el modelo no pasó el control de citas, pero los fragmentos
permitieron obtener datos literales con sus referencias. Comprueba siempre
las páginas originales antes de aceptar una conclusión.

**No es necesario volver a cargar ni indexar los cinco artículos.**

## Verificación de esta versión

- 36 pruebas Python aprobadas; una prueba HTTP omitida porque en el entorno
  de comprobación faltan FastAPI/HTTPX.
- 3 pruebas de interfaz aprobadas.
- Falta probar la generación con tu Ollama local y el corpus real instalado
  en tu equipo, así como comprobar científicamente las respuestas.
