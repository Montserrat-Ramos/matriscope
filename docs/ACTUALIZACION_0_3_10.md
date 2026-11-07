# MatriScope 0.3.10 — Propiedades, métodos experimentales y matriz legible

## Problema identificado en la prueba con cinco artículos

La versión 0.3.9 seleccionaba correctamente las páginas de resultados,
pero en `metals-13-00330-v2.pdf` (página 12) mostró «sin relación experimental
explícita», aunque el fragmento distinguía porcentajes de porosidad del
0.0009 % y 0.0003 % asociados respectivamente a los modelos óptico y XCT.

La interfaz mostraba también párrafos y listas extensos dentro de una
tabla horizontal, lo que dificultaba consultar los resultados por artículo.

## Cambios principales

1. **Porosidad por método:** distingue pares explícitos de porcentajes
   asociados a modelos de microscopía óptica y tomografía XCT mediante la
   relación «respectively». No los interpreta como densidad relativa.
2. **Contraste cualitativo:** cuando el pasaje lo dice, registra qué método
   detectó mayor porosidad en los distintos rangos de potencia o energía.
   Este hallazgo se limita estrictamente a las condiciones del estudio.
3. **Otras propiedades:** reconoce intervalos explícitos de tamaño de poro
   en µm, dureza en HV y rugosidad Ra/Rz, conservando las unidades.
4. **Equipos:** identifica el nombre de la impresora mencionado en un
   antecedente científico junto con una cifra de porosidad, si aparece
   expresamente en la misma oración o su continuación inmediata.
5. **Presentación:** cambia la tabla extensa por una lista de tarjetas,
   una por artículo. Cada tarjeta contiene variables, valores de los
   resultados, métodos/condiciones y un pasaje original que se puede
   desplegar. También queda disponible el listado completo de fragmentos.
6. **Resumen de evidencia:** además de las relaciones energía-densidad,
   identifica en qué fuentes aparecen valores de porosidad y comparaciones
   cualitativas de técnicas de medición.

## Actualizar en Windows sin perder el proyecto

1. Detén Uvicorn con `Ctrl + C`.
2. Crea una copia de seguridad de `matriscope-app/data` en otro lugar.
3. Extrae `MatriScope_v0.3.10_Metodos_y_Comparacion.zip`.
4. Copia los archivos del programa a tu instalación existente. Conserva
   **`data/`, `.env`, todos los PDF originales y tu configuración**. No borres
   ni reemplaces la base de datos SQLite existente.
5. Ejecuta desde la carpeta `matriscope-app`:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn servicio.api.main:app --host 127.0.0.1 --port 8010 --reload
   ```

6. Comprueba la versión `0.3.10` en `http://127.0.0.1:8010/openapi.json`
   y, si aparece la interfaz antigua, recarga con `Ctrl + F5`.

**No es necesario volver a indexar los artículos.**

## Pregunta para repetir la prueba

> Compara los resultados reportados por los diferentes artículos sobre
> la relación entre densidad volumétrica de energía, porosidad y densidad
> relativa del acero inoxidable 316L fabricado mediante LPBF. Identifica
> coincidencias, diferencias, valores experimentales y sus fuentes.

## Comprobaciones esperadas

- En `materials-15-06672-v2.pdf`, conservar los umbrales de 79 y 103 J/mm³
  con 99.5 % y 99.9 % respectivamente, si el pasaje se recupera.
- En `metals-11-00832-v3.pdf`, conservar 45–125 J/mm³ con densidad
  mayor que 99.8 %, si ese intervalo aparece entre los fragmentos.
- En `jmmp-08-00035.pdf`, diferenciar 99.41 % por Arquímedes y 99.9 %
  por análisis de imágenes, sin asociar automáticamente 125 J/mm³ a esos
  resultados si el documento no establece esa correspondencia.
- En `materials-18-00435-v2.pdf`, mantener 104.52 J/mm³ y 0.38 % de
  porosidad como **antecedente citado**, identificando Renishaw AM 250 si
  se menciona en el pasaje.
- En `metals-13-00330-v2.pdf`, identificar 0.0009 % y 0.0003 % de porosidad
  para los modelos óptico y XCT, respectivamente, sin confundir porosidad
  con densidad relativa.
- Al pedir la densidad relativa del 99.7 %, mantener la abstención cuando
  no exista una correspondencia cuantitativa explícita.

## Límites de interpretación

La comparación es **documental y preliminar**. El sistema no valida por sí
solo incertidumbres, diseño experimental, métodos de medición, tablas,
gráficas, datos suplementarios ni comparabilidad física de los artículos.
Los patrones de extracción cubren formulaciones textuales reconocibles,
pero no todos los estilos de redacción científica. Toda conclusión debe
revisarse en los PDF originales y su contexto.

## Pruebas técnicas

- 54 pruebas de Python aprobadas; una prueba HTTP omitida porque el entorno
  de pruebas no dispone de FastAPI/HTTPX.
- 5 pruebas de interfaz aprobadas.
- Falta repetir la prueba con tus cinco PDF en Windows y comprobar el aspecto
  visual en tu navegador.
