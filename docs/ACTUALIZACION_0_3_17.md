# MatriScope 0.3.17 — Control de traducciones y segundo modelo

## Resultado de la prueba que motivó la actualización

En la consulta P03 sobre energía y porosidad, `qwen2.5:3b` tradujo dos de
cinco fragmentos y rechazó otros tres. El indicador global alcanzó el 100 %
porque **terminó de procesar las cinco fuentes**, aunque las tres traducciones
rechazadas debían conservar su pasaje original.

La versión 0.3.17 separa expresamente ambas métricas y permite volver a
intentar los fragmentos fallidos con el modelo alternativo.

## Cambios comprobables

1. **Resumen inequívoco:** `Procesamiento de fuentes finalizado` al 100 % e
   información `2 de 5 fuentes traducidas · 3 con errores`.
2. **Diferencias numéricas:** el backend incluye `detalle_validacion` con
   listas de valores originales ausentes (`faltantes`) y valores añadidos o
   diferentes (`adicionales`) cuando corresponda. Esto facilita diagnosticar
   fallos sin dar por válida una traducción problemática.
3. **Porcentajes equivalentes:** `0.38%`, `0,38%` y `0,38 %` conservan las
   mismas firmas de cifras y unidades. Cambios reales como `0.38` a `0.83`
   continúan rechazándose; también se comprueba el signo negativo.
4. **Traducción científica:** se añaden equivalencias para *stress risers*
   y se rechazan expresiones incorrectas frecuentes. La revisión lingüística
   sigue siendo parcial y no sustituye la revisión humana.
5. **Reintento manual:** en un pasaje con estado `fallo`, si existe otro modelo
   local, aparece un botón `Reintentar con <modelo>`. Su trabajo progresa en
   la misma barra. Si tampoco supera la validación, el original permanece.
6. **Conservación:** no cambia el esquema SQLite, la indexación de PDF, los
   modelos de embeddings ni los controles de citas del RAG.

## Cómo actualizar en Windows

1. Detén el servicio con `Ctrl + C` y conserva una copia del directorio de
   datos y de la configuración propia.
2. Descomprime esta versión en una carpeta nueva y copia tus datos de la
   instalación anterior si es necesario. No reindexes los documentos.
3. Comprueba los modelos disponibles:

   ```powershell
   ollama list
   ```

   Si falta uno, instálalo cuando tengas conexión:

   ```powershell
   ollama pull qwen2.5:3b
   ollama pull llama3.2:3b
   ```

4. Desde `matriscope-app` instala dependencias y ejecuta la API:

   ```powershell
   python -m pip install -r requirements.txt
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

5. Abre `http://127.0.0.1:8010`, recarga con `Ctrl + F5` y ejecuta P03.

## Pruebas de aceptación sugeridas

- Con `qwen2.5:3b` y `hybrid`, observar las barras individuales.
- Si una fuente falla, comprobar que su pasaje original permanece visible,
  que no se da por aprobada y que el diagnóstico distingue posibles cambios
  de números/unidades.
- Pulsar `Reintentar con llama3.2:3b` y comprobar que la barra empieza de nuevo,
  que el resultado indica el segundo modelo y que se aplican los mismos
  controles científicos.
- Verificar manualmente F2/F4/F5 en Windows contra el PDF. No podemos afirmar
  que el nuevo modelo los traducirá correctamente sin esa ejecución real.

## Límites

- Las traducciones siguen siendo automáticas. La concordancia semántica y la
  fidelidad al artículo requieren cotejo del pasaje original.
- Un porcentaje de procesamiento finalizado **no certifica** calidad.
- El reintento no cambia el contenido original, los metadatos ni las citas.
