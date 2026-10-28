# ollama

**Responsable:** Juan

Herramientas para evaluar y configurar el modelo local de Ollama.

| Archivo | Contenido |
|---|---|
| [`benchmark_modelos.py`](benchmark_modelos.py) | Mide rendimiento, llamadas a herramientas y calidad en español, y guarda las salidas crudas (JSONL) |
| [`resumir_resultados.py`](resumir_resultados.py) | Genera las tablas Markdown a partir de las salidas crudas |

Resultados, decisión del modelo y pasos para repetir la prueba: [`docs/benchmarks/ollama-pruebas-modelos.md`](../../docs/benchmarks/ollama-pruebas-modelos.md).
