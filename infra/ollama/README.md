# ollama

**Responsable:** Juan

Configuración de Ollama y del modelo local elegido.

- `benchmark_modelos.py`: mide rendimiento, llamadas a herramientas y calidad en español de los modelos locales y guarda las salidas crudas (JSONL). Ver `docs/benchmarks/ollama-pruebas-modelos.md`.
- `resumir_resultados.py`: genera las tablas Markdown a partir de las salidas crudas.

```
python benchmark_modelos.py --salida ../../docs/benchmarks/resultados
python resumir_resultados.py ../../docs/benchmarks/resultados > ../../docs/benchmarks/resultados/resumen.md
```

Requiere Ollama en marcha en `http://localhost:11434` y los modelos descargados. Usa solo la biblioteca estándar de Python.
