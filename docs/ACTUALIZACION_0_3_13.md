# MatriScope 0.3.13 — Corrección de traducción detenida

## Incidencia comprobada por la usuaria

Después de ejecutar P03 en 0.3.12, transcurrido un minuto los cinco pasajes
seguían con el mensaje «Traduciendo fragmento al español…».

## Causa técnica probable

El cliente enviaba hasta cinco fragmentos de unas 850 letras cada uno a una
sola solicitud de `llama3.2:3b`, con salida JSON extensa y tiempo de espera
del adaptador configurado a 90 segundos. En hardware local esto puede demorar
considerablemente. No se dispone de la traza de Ollama de esa ejecución para
confirmar si la causa concreta fue saturación, demora de generación o bloqueo.

## Corrección

1. La interfaz divide la traducción en solicitudes **de un solo fragmento**.
2. Prioriza `[F#]` utilizados en la respuesta para mostrar primero la evidencia
   que fundamenta las afirmaciones científicas.
3. Muestra estados individuales: «Pendiente de traducción», «Traduciendo este
   fragmento», «Traducción al español», o un aviso de fallo verificable.
4. Usa un límite de 35 segundos por generación del servidor y aborta la
   solicitud del navegador tras 40 segundos. Un error permite continuar con
   otras fuentes sin bloquear la consulta principal.
5. Continúa verificando que la traducción conserve todos los números y las
   unidades del original. Si la verificación falla, presenta el original.
6. Mantiene el texto inglés para verificación y no edita PDFs o SQLite.

## Instalación

1. Detener Uvicorn con `Ctrl + C`.
2. Respaldar `data/` y `.env` de la instalación existente.
3. Extraer la versión 0.3.13 en una carpeta nueva y copiar los datos ya
   indexados sin borrar los originales.
4. Desde `matriscope-app`, ejecutar:

   ```powershell
   python -m pip install -r requirements.txt
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

5. Confirmar la versión `0.3.13` en `http://127.0.0.1:8010/openapi.json`.
6. Hacer `Ctrl + F5` en el navegador y repetir la pregunta P03.

## Resultado esperado

- La síntesis científica debe aparecer primero.
- Cada pasaje empieza como pendiente; los citados se traducen primero.
- No hay una única espera por todos los fragmentos.
- Si uno falla, el sistema muestra que la traducción no finalizó y deja el
  fragmento original visible; sigue procesando los restantes.
- Los pasajes que sí se traducen muestran un desplegable con su texto original.

## Verificación técnica

- 65 pruebas de Python sin fallos (una prueba omitida por dependencias locales).
- 8 pruebas de interfaz aprobadas.
- El rendimiento real y la calidad de traducción aún deben probarse con
  Ollama en la computadora de la usuaria.
