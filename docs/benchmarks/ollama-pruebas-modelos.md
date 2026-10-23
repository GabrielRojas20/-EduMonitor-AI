# Pruebas de modelos locales con Ollama (S1-12)

**Responsable:** Juan
**Fecha de la medición:** 2026-10-22 (segunda versión, tras la revisión del PR #3)
**Ollama:** 0.40.8

## Cambios respecto de la primera versión

La primera versión midió una respuesta corta, no 200 tokens, y no conservó las salidas crudas. Esta versión:

- Fija una longitud comparable: todas las respuestas llegan al tope de 200 tokens y se reporta la cantidad real de tokens generados.
- Guarda las salidas crudas de cada ejecución en `docs/benchmarks/resultados/` y el script que las produce en `infra/ollama/benchmark_modelos.py`.
- Añade pruebas de llamadas a herramientas con casos en los que no se debe llamar a ninguna, y de calidad en español con datos de ejemplo.
- **Los valores anteriores no se reproducen y quedan reemplazados.** Por ejemplo, el "2,2 s" con el modelo cargado en realidad ronda 2,4 a 2,7 s. No se conservaron las salidas de aquella medición, por eso no se pueden confirmar.
- Como resultado, **la decisión del modelo cambia** (ver "Decisión").

## Equipo de prueba

| Componente | Valor |
|---|---|
| CPU | Intel Core i5-1035G1 (4 núcleos, 8 hilos) |
| RAM | 11,7 GB |
| GPU | Intel UHD Graphics (integrada). Ollama no la usa: `size_vram` = 0 en los tres modelos |
| Ejecución | 100 % CPU, contexto de 4096 tokens |

## Método

- Modelos: `qwen3:1.7b`, `qwen2.5:3b` y `llama3.2:3b`, con la cuantización por defecto de Ollama. Los tres se evalúan con `think: false`.
- Cada medición se repite 3 veces, con temperatura 0,3 y semillas 1, 2 y 3. El script y las salidas crudas están en el repositorio (ver "Cómo reproducir").
- **Rendimiento:** se pide un texto de al menos 400 palabras con tope de 200 tokens (`num_predict = 200`). Los tres modelos generaron exactamente 200 tokens en todas las ejecuciones.
  - *Primera respuesta:* tiempo, medido por el cliente, hasta recibir el primer fragmento de texto de la respuesta en streaming.
  - *En frío:* antes de cada ejecución se descarga el modelo con `keep_alive: 0` y se espera a que `/api/ps` quede vacío. Incluye la carga del modelo en memoria (`load_duration`).
  - *Cargado:* el modelo ya está en memoria, tras una precarga con `keep_alive: "30m"`.
  - *Tokens/s:* `eval_count / eval_duration` que informa Ollama.
- **Memoria:** columna `size` de `GET /api/ps` justo después de cargar el modelo. Es la memoria que Ollama reserva para el modelo y su contexto de 4096 tokens. No es la memoria residente del proceso ni incluye el resto del sistema.
- **Llamadas a herramientas:** se ofrecen tres herramientas de ejemplo (`listar_cursos`, `obtener_calificaciones` e `identificar_alertas`), solo para esta prueba y distintas del contrato del agente (S1-11). Hay 6 casos × 3 repeticiones: 4 casos en los que se debe llamar a una herramienta concreta con argumentos exactos, y 2 en los que no se debe llamar a ninguna (pedir cambiar una nota y un saludo).
  - *Tiempo medio:* promedio de la petición completa, sin streaming, hasta que el modelo decide. Incluye el procesamiento del mensaje y de las definiciones de las herramientas y la generación de la llamada, o del texto cuando no llama. Con el modelo ya cargado. No incluye ejecutar la herramienta.
- **Calidad en español:** el modelo llama a la herramienta, se le entrega un resultado simulado y se evalúa su respuesta final. Hay dos escenarios: datos correctos (una nota de 8,5 y una entrega sin nota) y una herramienta que falla (`MOODLE_UNAVAILABLE`). Criterios, todos automáticos:
  - *Cifras respaldadas:* todo número de la respuesta aparece en el resultado de la herramienta o en la pregunta.
  - *En español:* contiene palabras comunes del español y ninguna palabra común del inglés.
  - *Avisa si falla:* en el escenario de falla, la respuesta indica que no pudo obtener el dato.
  - *Ciclo completo:* tiempo de la petición que decide llamar a la herramienta más el de la respuesta final, con el modelo cargado.

## Resultados

### Rendimiento (200 tokens generados en todos los casos)

| Modelo | Memoria (Ollama) | Situación | Carga (s) | Primera respuesta (s) | Tokens/s | Respuesta completa (s) |
|---|---|---|---|---|---|---|
| `qwen3:1.7b` | 1,89 GB | En frío | 3,99 | 6,70 | 14,5 | 20,5 |
| `qwen3:1.7b` | | Cargado | 0,02 | 2,39 | 13,1 | 18,1 |
| `qwen2.5:3b` | 2,17 GB | En frío | 6,06 | 9,65 | 9,1 | 31,8 |
| `qwen2.5:3b` | | Cargado | 0,01 | 2,59 | 9,0 | 24,8 |
| `llama3.2:3b` | 2,57 GB | En frío | 5,81 | 9,19 | 8,6 | 32,3 |
| `llama3.2:3b` | | Cargado | 0,01 | 2,65 | 9,1 | 24,7 |

Primera respuesta en frío, por repetición (s): `qwen3:1.7b` 8,5 / 5,9 / 5,7; `qwen2.5:3b` 11,6 / 8,5 / 8,8; `llama3.2:3b` 10,3 / 9,1 / 8,2. La primera ejecución de cada modelo es la más lenta, probablemente porque el archivo aún no está en la caché del sistema. Con solo 3 repeticiones, el valor en frío de los modelos de 3B queda cerca de la meta de 10 s y a veces la supera.

### Llamadas a herramientas (aciertos / intentos)

| Modelo | Cursos | Notas de un estudiante | Notas del curso | Alertas | Cambiar una nota (no debe llamar) | Saludo (no debe llamar) | Total | Tiempo medio (s) |
|---|---|---|---|---|---|---|---|---|
| `qwen3:1.7b` | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | **18/18** | 5,0 |
| `qwen2.5:3b` | 3/3 | 3/3 | 2/3 | 3/3 | 0/3 | 3/3 | 14/18 | 7,8 |
| `llama3.2:3b` | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | 0/3 | 12/18 | 4,4 |

Fallos:
- `qwen2.5:3b` y `llama3.2:3b` llamaron a `obtener_calificaciones` ante "cambia la nota del estudiante 4 a 10", aunque no hay herramienta de escritura.
- `llama3.2:3b` llamó a una herramienta ante un saludo en las 3 repeticiones.
- `qwen2.5:3b` llamó a `listar_cursos` en vez de `obtener_calificaciones` en una repetición de "notas del curso".

### Calidad en español con resultado de herramienta (aciertos / intentos)

| Modelo | Escenario | Cifras respaldadas | En español | Avisa si falla | Todo correcto | Ciclo completo (s) |
|---|---|---|---|---|---|---|
| `qwen3:1.7b` | Datos correctos | 3/3 | 3/3 | 3/3 | 3/3 | 15,4 |
| `qwen3:1.7b` | Herramienta falla | 3/3 | 3/3 | 3/3 | 3/3 | 11,7 |
| `qwen2.5:3b` | Datos correctos | 3/3 | 3/3 | 3/3 | 3/3 | 21,7 |
| `qwen2.5:3b` | Herramienta falla | 3/3 | 3/3 | 3/3 | 3/3 | 16,0 |
| `llama3.2:3b` | Datos correctos | 3/3 | 3/3 | 3/3 | 3/3 | 16,7 |
| `llama3.2:3b` | Herramienta falla | 3/3 | 3/3 | 3/3 | 3/3 | 13,7 |

Los tres modelos cumplen estos criterios en todas las repeticiones: no inventaron cifras, respondieron en español y avisaron cuando la herramienta falló. En estas pruebas no distinguen entre los modelos.

## Precarga con `keep_alive`

Sí se precargará el modelo para la demostración. Con la carga en frío la primera respuesta puede superar los 10 s en los modelos de 3B. Si el modelo ya está cargado, baja a unos 2,4 a 2,7 s.

- El `agent-service` enviará `keep_alive: "30m"` (o se configurará `OLLAMA_KEEP_ALIVE`) en las peticiones a Ollama.
- El guion de la demostración incluirá una petición de precarga antes de empezar. En esta medición, precargar tardó 5,3 s (`qwen3:1.7b`), 6,4 s (`qwen2.5:3b`) y 7,4 s (`llama3.2:3b`).
- Por defecto Ollama descarga el modelo tras 5 minutos sin uso, así que sin esta configuración una pausa larga volvería a producir una primera respuesta en frío.

## Lectura de los resultados

- **Meta de primera respuesta (10 s o menos):** con el modelo cargado, los tres la cumplen con holgura (2,4 a 2,7 s). En frío, `qwen3:1.7b` la cumple (5,7 a 8,5 s); los de 3B quedan entre 8,2 y 11,6 s, es decir, a veces la superan.
- **Meta de respuesta completa (60 s o menos):** una respuesta de 200 tokens tarda entre 18 y 25 s con el modelo cargado. Un ciclo con una herramienta tarda entre 12 y 22 s. Un chat con varias herramientas encadenadas en un modelo de 3B puede acercarse al límite.
- **Llamadas a herramientas:** `qwen3:1.7b` fue el único que no llamó a ninguna cuando no correspondía.
- **Memoria:** los tres usan entre 1,89 y 2,57 GB, muy por debajo de los 11,7 GB. El de mayor consumo es `llama3.2:3b`, y el de menor, `qwen3:1.7b`.

## Decisión

**Modelo principal propuesto: `qwen3:1.7b`.** Es el cambio respecto de la primera versión, y se sustenta en criterios medidos:

| Criterio | `qwen3:1.7b` | `qwen2.5:3b` | `llama3.2:3b` |
|---|---|---|---|
| Aciertos con herramientas | 18/18 | 14/18 | 12/18 |
| No llama a herramientas al pedir cambiar una nota | 3/3 | 0/3 | 0/3 |
| Primera respuesta en frío (media) | 6,7 s | 9,7 s | 9,2 s |
| Velocidad | 13 a 14 tok/s | 9 tok/s | 9 tok/s |
| Memoria | 1,89 GB | 2,17 GB | 2,57 GB |
| Español, cifras y aviso de falla | 3/3 | 3/3 | 3/3 |

**Alternativa:** `qwen2.5:3b`, si los 20 escenarios de evaluación del Sprint 2 muestran que la calidad de las respuestas de `qwen3:1.7b` no alcanza.

### Limitaciones de esta prueba

- **Muestra pequeña:** 3 repeticiones por caso y pocos casos. Una diferencia de un acierto no es concluyente.
- **Criterios automáticos:** la prueba de español detecta palabras comunes; no evalúa la redacción, la utilidad ni la calidad de las recomendaciones. Eso lo cubre el conjunto de 20 escenarios del Sprint 2.
- **Datos y herramientas de ejemplo:** no son los del contrato final. Las herramientas con ruta aún por definir (S1-11) pueden cambiar los resultados.
- **Un solo equipo:** los tiempos dependen de este computador y del estado del sistema. Hay que repetirlos en el equipo de la demostración, que el Product Owner aún debe confirmar.
- **Memoria:** es la reserva que informa Ollama con contexto de 4096 tokens; con un contexto mayor sube.
- **Modo de razonamiento:** se desactivó en `qwen3:1.7b`. Si se activa, las respuestas serían más lentas.
- **Estabilidad:** solo se midió la repetición con semillas distintas; no se probaron periodos largos de uso.

## Cómo reproducir

1. Instalar Ollama 0.40.8 y descargar los modelos:
   ```
   ollama pull qwen3:1.7b
   ollama pull qwen2.5:3b
   ollama pull llama3.2:3b
   ```
2. Con el servidor de Ollama en marcha y sin otros programas pesados abiertos:
   ```
   cd infra/ollama
   python benchmark_modelos.py --salida ../../docs/benchmarks/resultados
   python resumir_resultados.py ../../docs/benchmarks/resultados > ../../docs/benchmarks/resultados/resumen.md
   ```
3. Salidas crudas (una línea JSON por ejecución, con tiempos, tokens y texto de cada respuesta):
   - `docs/benchmarks/resultados/qwen3_1.7b.jsonl`
   - `docs/benchmarks/resultados/qwen2.5_3b.jsonl`
   - `docs/benchmarks/resultados/llama3.2_3b.jsonl`
   - `docs/benchmarks/resultados/meta.json` (versión de Ollama y parámetros)
   - `docs/benchmarks/resultados/resumen.md` (tablas generadas a partir de lo anterior)
