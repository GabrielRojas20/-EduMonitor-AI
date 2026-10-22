# Pruebas de modelos locales con Ollama (S1-12)

**Responsable:** Juan
**Fecha:** 2026-10-22
**Ollama:** 0.40.8

## Equipo de prueba

| Componente | Valor |
|---|---|
| CPU | Intel Core i5-1035G1 (4 núcleos, 8 hilos) |
| RAM | 11,7 GB |
| GPU | Intel UHD Graphics (integrada, sin aceleración) |
| Ejecución | 100 % CPU |

## Método

- Modelos: `qwen3:1.7b`, `qwen2.5:3b` y `llama3.2:3b`, con la cuantización por defecto de Ollama.
- Respuesta de chat: pregunta de tres frases, temperatura 0 y máximo de 200 tokens de salida. Se mide con el modelo ya cargado (promedio de 3 ejecuciones).
- Carga en frío: primera respuesta justo después de descargar el modelo de memoria.
- Tool calling: se ofrece la herramienta `obtener_calificaciones(course_id, student_id)` y se pide "las calificaciones del estudiante 4 en el curso 2". Se acepta si el modelo llama a la herramienta con `course_id=2` y `student_id=4` (3 ejecuciones).
- En `qwen3:1.7b` se desactivó el modo de razonamiento (`think: false`).

## Resultados

| Modelo | Memoria | Primera respuesta en frío | Primera respuesta | Respuesta (200 tokens) | Velocidad | Tool calling | Tiempo con herramienta |
|---|---|---|---|---|---|---|---|
| `qwen3:1.7b` | 1,9 GB | 7,0 s | 2,2 s | 6,4 s | 16,0 tok/s | 3/3 | 4,9 s |
| `qwen2.5:3b` | 2,2 GB | 11,7 s | 2,2 s | 17,2 s | 9,4 tok/s | 3/3 | 6,8 s |
| `llama3.2:3b` | 2,6 GB | 11,7 s | 2,2 s | 13,3 s | 9,2 tok/s | 3/3 | 5,8 s |

Metas del plan (sección 8.1): primera respuesta en 10 s o menos y respuesta completa en 60 s o menos.

## Lectura de los resultados

- Los tres modelos cumplen la meta de primera respuesta con el modelo cargado (2,2 s). En frío, solo `qwen3:1.7b` (7,0 s) cumple los 10 s; los dos de 3B tardan 11,7 s.
- Los tres llamaron correctamente a la herramienta en las 3 ejecuciones.
- Con 9 a 16 tokens por segundo, una respuesta de unos 400 tokens tardaría entre 25 y 45 s. Un chat que encadene varias herramientas puede acercarse a los 60 s en los modelos de 3B.
- Consumen entre 1,9 y 2,6 GB, muy por debajo de los 11,7 GB disponibles.

## Limitaciones de esta prueba

- La prueba de tool calling usa una sola herramienta y una consulta simple. No mide la calidad de las respuestas ni el uso de varias herramientas encadenadas; eso lo cubrirá el conjunto de 20 escenarios del Sprint 2.
- Los tiempos son de un solo equipo y dependen de su estado en el momento de la medición.
- No se probó un modelo de 7B u 8B: con 11,7 GB de RAM y sin GPU se espera que sea demasiado lento.

## Decisión provisional

- **Modelo principal propuesto:** `qwen2.5:3b`. Es el de mayor tamaño con tiempos aceptables y llamó bien a la herramienta. Falta confirmar su calidad con los escenarios de evaluación.
- **Alternativa rápida:** `qwen3:1.7b`, para equipos con menos recursos o si el tiempo de respuesta completa supera la meta.
- La decisión se confirma al final del Sprint 1 (punto de decisión del riesgo de hardware, sección 10 del plan) y se revisa al ejecutar los escenarios de evaluación.
- Equipo de la demostración: pendiente de confirmar con el Product Owner. Los tiempos deben repetirse en ese equipo.

## Cómo reproducir

```
ollama pull qwen3:1.7b
ollama pull qwen2.5:3b
ollama pull llama3.2:3b
```

La prueba llama a la API local de Ollama (`http://localhost:11434/api/chat`) con el mensaje y la herramienta descritos en el método.
