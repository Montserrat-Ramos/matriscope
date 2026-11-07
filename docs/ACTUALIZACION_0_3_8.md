# MatriScope 0.3.8 — Abstención fundamentada y comparación documental

Esta versión utiliza los resultados de las pruebas con acero inoxidable 316L.
Las consultas por 99.5 % y 99.9 % ya recuperan relaciones explícitas con
79 y 103 J/mm³, respectivamente. La consulta por 99.7 % mostró un problema:
una síntesis generativa asociaba indebidamente el umbral de 79 J/mm³ con
un porcentaje que el pasaje no reportaba específicamente.

## Correcciones

1. **Porcentaje específico sin relación verificable.** Si el sistema no
   encuentra una relación cuantitativa explícita en los fragmentos recuperados,
   responde que la evidencia es insuficiente. No calcula un valor interpolado.
2. **Comparación de estudios.** Para preguntas comparativas se seleccionan
   pasajes de diferentes documentos, con una matriz de variables, referencias
   y evidencia textual. Esta matriz necesita interpretación y revisión humana.
3. **Comprobación numérica de citas.** Los porcentajes y las cantidades con
   unidades en salidas generativas deben aparecer en los pasajes citados.
   El control no sustituye una revisión científica de causalidad o metodología.
4. **Caché conservadora.** Las respuestas generativas automáticas no se
   almacenan como resultados verificados; se invalida la clave de la versión
   anterior. Los datos científicos y proyectos persisten.

## Instalar en Windows

1. Detén Uvicorn con `Ctrl + C`.
2. Respalda tu carpeta `matriscope-app/data` de la instalación actual.
3. Descomprime `MatriScope_v0.3.8_Validacion_y_Comparacion.zip`.
4. Actualiza el código conservando `data/`, `.env`, los PDF originales y
   cualquier configuración personal. No elimines la base SQLite.
5. Desde la carpeta de la aplicación ejecuta:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

6. Comprueba `0.3.8` en `http://127.0.0.1:8010/openapi.json` y el servicio
   en `http://127.0.0.1:8010/api/health`.

No se requiere volver a indexar los cinco artículos.

## Pruebas manuales sugeridas

**Prueba A (debe recuperar cifra):**

> ¿Qué valor de energía corresponde a una densidad relativa del 99.9 %?
> Indica la fuente y la página.

Esperado: 103 J/mm³, si el fragmento de *Materials* 2022 sigue recuperándose.

**Prueba B (debe abstenerse sin interpolar):**

> ¿Qué energía se requiere para alcanzar una densidad relativa del 99.7 %
> en el acero inoxidable 316L? Indica el dato experimental y la página.

Esperado: no se encontró una correspondencia explícita en los fragmentos
recuperados; no debe asignar arbitrariamente 79 ni 103 J/mm³.

**Prueba C (debe generar matriz de evidencia):**

> Compara las coincidencias y diferencias que reportan los artículos sobre
> densidad relativa y porosidad del acero inoxidable 316L fabricado por LPBF.

Esperado: tabla con al menos dos documentos diferentes, referencias y pasajes.
La tabla no sustituye un análisis experto de métodos y resultados.

## Estado de verificación

- 45 pruebas Python aprobadas; una prueba HTTP fue omitida por no disponer de
  las dependencias FastAPI/HTTPX en este entorno de pruebas.
- 4 pruebas de interfaz aprobadas, incluida la visualización de la comparación.
- Falta validación de extremo a extremo con Ollama y tu corpus real en Windows.
