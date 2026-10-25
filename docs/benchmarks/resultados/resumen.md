### Rendimiento (3 repeticiones por fila)

| Modelo | Situación | Carga del modelo (s) | Primera respuesta (s) | Tokens generados | Tokens/s | Total (s) |
|---|---|---|---|---|---|---|
| `llama3.2:3b` | En frío | 5.81 | 9.19 | 200 | 8.64 | 32.34 |
| `llama3.2:3b` | Cargado | 0.01 | 2.65 | 200 | 9.09 | 24.71 |
| `qwen2.5:3b` | En frío | 6.06 | 9.65 | 200 | 9.06 | 31.81 |
| `qwen2.5:3b` | Cargado | 0.01 | 2.59 | 200 | 9.0 | 24.8 |
| `qwen3:1.7b` | En frío | 3.99 | 6.7 | 200 | 14.5 | 20.51 |
| `qwen3:1.7b` | Cargado | 0.02 | 2.39 | 200 | 13.09 | 18.1 |

### Detalle de la primera respuesta en frío (s)

| Modelo | Rep. 1 | Rep. 2 | Rep. 3 | Precarga con keep_alive (s) |
|---|---|---|---|---|
| `llama3.2:3b` | 10.267 | 9.059 | 8.237 | 7.438 |
| `qwen2.5:3b` | 11.581 | 8.524 | 8.834 | 6.409 |
| `qwen3:1.7b` | 8.518 | 5.933 | 5.662 | 5.281 |

### Memoria (`/api/ps` tras cargar el modelo)

| Modelo | Tamaño (GB) | En GPU (GB) | Contexto |
|---|---|---|---|
| `llama3.2:3b` | 2.57 | 0.0 | 4096 |
| `qwen2.5:3b` | 2.17 | 0.0 | 4096 |
| `qwen3:1.7b` | 1.89 | 0.0 | 4096 |

### Llamadas a herramientas (aciertos / intentos)

| Modelo | alertas | cursos | fuera_alcance | notas | notas_curso | saludo | Total | Tiempo medio (s) |
|---|---|---|---|---|---|---|---|---|
| `llama3.2:3b` | 3/3 | 3/3 | 0/3 | 3/3 | 3/3 | 0/3 | 12/18 | 4.36 |
| `qwen2.5:3b` | 3/3 | 3/3 | 0/3 | 3/3 | 2/3 | 3/3 | 14/18 | 7.82 |
| `qwen3:1.7b` | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 18/18 | 4.99 |

### Calidad con resultado de herramienta (aciertos / intentos)

| Modelo | Caso | Cifras respaldadas | En español | Avisa si falla | Todo correcto | Ciclo completo (s) |
|---|---|---|---|---|---|---|
| `llama3.2:3b` | fidelidad_notas | 3/3 | 3/3 | 3/3 | 3/3 | 16.66 |
| `llama3.2:3b` | falla_herramienta | 3/3 | 3/3 | 3/3 | 3/3 | 13.67 |
| `qwen2.5:3b` | fidelidad_notas | 3/3 | 3/3 | 3/3 | 3/3 | 21.7 |
| `qwen2.5:3b` | falla_herramienta | 3/3 | 3/3 | 3/3 | 3/3 | 16.01 |
| `qwen3:1.7b` | fidelidad_notas | 3/3 | 3/3 | 3/3 | 3/3 | 15.38 |
| `qwen3:1.7b` | falla_herramienta | 3/3 | 3/3 | 3/3 | 3/3 | 11.74 |
