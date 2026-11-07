# MatriScope 0.3.15 — Traducción científica y modelos independientes

## Problema observado

En la prueba de los cinco artículos sobre 316L/LPBF, dos fragmentos se
tradujeron con terminología incorrecta y tres no terminaron o fueron
rechazados. El sistema no distinguía en la pantalla si la causa era un
tiempo agotado, un JSON inválido, una cifra modificada o la indisponibilidad
de Ollama. Además, el modelo de traducción se tomaba del servidor y no del
selector principal de la interfaz.

## Cambios

1. En **Explorador semántico**, seleccionar el modelo principal, modo de
   respuesta y **modelo para traducir fuentes**.
2. Si eliges «Usar el modelo principal», las traducciones se enviarán al
   modelo seleccionado para la pregunta. Puedes elegir otro modelo solo
   para traducción. El modelo debe estar instalado en Ollama.
3. Cada solicitud de traducción procesa **un segmento corto**; la interfaz
   llama repetidamente para completar la fuente y muestra su avance.
   Cada llamada tiene un máximo de 30 segundos de generación en el servidor
   y 36 segundos en el navegador.
4. Si el modelo altera una cifra, unidad o término protegido, el servidor
   ejecuta como máximo **un reintento adicional** en la siguiente llamada.
   Si vuelve a fallar, devuelve un diagnóstico concreto y conserva el pasaje
   original. La vista no espera indefinidamente.
5. Las traducciones válidas se guardan en memoria con clave de proyecto,
   fragmento y modelo. El estado parcial también permanece en la memoria
   mientras el servidor siga ejecutándose.
6. El resultado de la consulta indica si el modo `hybrid` respondió por
   extracción directa. **No significa que Ollama no haya sido utilizado
   después para traducir las fuentes.**

### Diagnósticos de traducción posibles

| Código | Motivo |
| --- | --- |
| `cifras_alteradas` | El modelo cambió una cantidad o número |
| `unidades_alteradas` | Cambió una unidad técnica o su número de apariciones |
| `terminologia_no_conservada` | No se conservó un término protegido del glosario |
| `respuesta_json_invalida` | Ollama no devolvió el contenido esperado |
| `tiempo_agotado` | Una llamada alcanzó el límite temporal |
| `ollama_no_disponible` | La llamada local falló |
| `validacion_global_fallida` | La traducción reunida no conservó los datos de todo el fragmento |

La validación léxica es limitada y **no sustituye un traductor científico ni
la revisión del PDF**. Los términos clave se incluyen en el prompt de
traducción y un filtro adicional impide algunas sustituciones ya observadas,
por ejemplo traducir `keyhole` como «agujero de lluvia».

## Instalación

1. Detener el servidor con `Ctrl + C`.
2. Respaldar `data/` y archivos de configuración de la versión anterior.
3. Extraer 0.3.15 en una carpeta nueva y copiar `data/` para conservar
   documentos y proyectos. No es necesario reindexar los PDF.
4. Instalar o comprobar modelos:

   ```powershell
   ollama pull qwen2.5:3b
   ollama pull llama3.2:3b
   ollama list
   ```

5. Desde `matriscope-app`:

   ```powershell
   python -m pip install -r requirements.txt
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

6. Abrir `http://127.0.0.1:8010` y pulsar `Ctrl + F5`.

## Prueba recomendada

Pregunta: «¿Qué relación describen los artículos entre la densidad volumétrica
de energía y la porosidad del acero 316L?»

- Ejecutar con modo `hybrid` y modelo principal `qwen2.5:3b`.
- Mantener traducción con «Usar el modelo principal» y observar el avance
  individual de los pasajes.
- Si aparece un fallo, revisar **Motivo** y consultar el original.
- Cambiar a `llama3.2:3b` como modelo de traducción y volver a consultar,
  manteniendo la pregunta y corpus. Esto no altera la selección del LLM de
  respuesta ni borra el documento indexado.
- En modo `generative`, comprobar que el resultado principal muestre el
  modelo ejecutado y citas verificables. «Comparar modelos» sigue aplicando
  el mismo corpus y las validaciones a ambos candidatos.

## Verificación y límites

- Pruebas automáticas con modelos dobles (sin red ni ejecución real de Ollama).
- Es necesario comprobar latencia, corrección de traducciones y distribución
  de tiempos en la computadora local antes de evaluar precisión científica.
