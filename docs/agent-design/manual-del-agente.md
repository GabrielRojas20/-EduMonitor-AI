# Manual del agente de EduMonitor AI

Este manual explica qué hace el agente, cómo se usa desde el chat, qué preguntas responde bien, cómo se prepara y se muestra en la demostración, y qué hacer si algo falla. Todo lo que dice se probó con el curso PRUEBA01 y el gateway real.

## Edu, el asistente

El agente de IA se presenta al docente con el nombre **Edu**. Es un colega cercano y sereno: tutea, habla en primera persona («te sugiero», «yo revisaría»), usa frases cortas y no hace elogios, exclamaciones ni bromas. Cuando un dato no está, lo dice con naturalidad y deja la decisión final al docente.

La personalidad solo afecta a la voz de las inferencias, las recomendaciones y los mensajes de ayuda o de rechazo, y a los textos de la interfaz. **Los hechos y las cifras no cambian:** los redacta el código a partir de los datos de las herramientas, y la validación final sigue descartando toda cifra sin respaldo. Edu no finge sentimientos, no opina sobre la vida personal de un estudiante y no hace diagnósticos.

Edu está en la página de cada curso, con el curso ya fijado, y guarda un historial de consultas por docente y curso en el navegador. En la documentación técnica se sigue llamando «agente de IA».

## 1. Qué es el agente

El agente es un servicio aparte (`services/agent-service`) que conversa con el docente desde la pantalla «Agente IA» de la interfaz. Usa un modelo de lenguaje local (`qwen3:1.7b`, con Ollama), por lo que no envía datos de estudiantes a servicios externos.

El agente **solo lee datos**. Consulta al gateway con el mismo token del docente, así que solo ve los cursos que ese docente tiene autorizados. No modifica calificaciones, no envía mensajes a estudiantes y no hace diagnósticos ni afirmaciones sobre el estado personal o psicológico de un estudiante.

Para no inventar datos, el código (no el modelo) redacta los **hechos** de cada respuesta a partir de lo que devuelven las herramientas, y una validación final descarta toda cifra que no exista en esos datos. El modelo solo redacta las **inferencias** y las **recomendaciones**, y únicamente cuando el docente pide interpretación.

## 2. Las cinco herramientas

| Herramienta | Qué responde | Pregunta de ejemplo |
|---|---|---|
| `listar_cursos` | Cursos autorizados, cantidad de estudiantes y última sincronización | «¿Qué cursos tengo?» |
| `obtener_calificaciones` | Notas y estado de cada entrega (calificada, pendiente de calificar, sin entrega) | «¿Qué falta por calificar?» |
| `obtener_progreso` | Indicadores del curso o de un estudiante: promedio, entrega, calificación, finalización y pendientes | «¿Cuál es el progreso de mis estudiantes?» |
| `identificar_alertas` | Alertas activas con su regla, valor observado, umbral y explicación | «¿Qué alertas tiene el curso?» |
| `generar_resumen` | Informe del curso: indicadores, hallazgos y alertas con su evidencia | «Genera un informe del curso PRUEBA01» |

## 3. Cómo leer una respuesta

Cada respuesta separa tres bloques:

- **Hechos:** lo que muestran los datos, con cifras exactas y la herramienta de la que salen («Fuentes»). Si un dato no está disponible, lo dice y nunca lo convierte en cero.
- **Inferencias:** interpretaciones prudentes que se apoyan en hechos concretos («Basado en hechos»).
- **Recomendaciones:** acciones concretas ligadas a un hallazgo. Son orientativas: las revisa el docente.

La respuesta muestra además la fecha de la última sincronización y el identificador de la traza (`Traza`), con el que se puede revisar después qué herramientas se usaron.

**Cuándo hay inferencias y recomendaciones.** Si la pregunta solo pide un dato («¿Qué cursos tengo?»), la respuesta trae solo hechos. Las recomendaciones aparecen cuando el docente pide análisis o interpretación: «qué me recomiendas», «analiza», «por qué», «cómo va» o «progreso».

**Curso elegido.** Arriba del chat hay un selector de curso. El agente usa ese curso aunque la pregunta no lo nombre («¿Qué alertas tiene el curso?»). Si el docente escribe un código de curso en la pregunta (por ejemplo, PRUEBA01), ese código manda sobre el selector.

## 3.1 Qué no hace

- No modifica notas: «Cambia la nota de Ana Pérez…» se rechaza con una explicación.
- No muestra datos de un curso que el docente no tiene autorizado: responde que no lo encontró entre los suyos.
- No responde fuera del alcance académico del curso ni hace predicciones sobre las personas.
- No sustituye el criterio del docente: las alertas no son diagnósticos.

## 4. Preguntas de la demostración

Se probaron con el curso PRUEBA01 y el curso seleccionado en la interfaz, tres veces seguidas cada una el 24 de noviembre de 2026. Los tiempos son los medidos con el modelo local en un equipo con poca memoria libre; con más memoria suelen ser menores.

| # | Pregunta | Qué se espera ver | Resultado de las 3 pruebas |
|---|---|---|---|
| 1 | «¿Qué falta por calificar?» | 1 registro pendiente de calificar, con el estudiante y el nombre real de la actividad | 3 de 3 correctas, 4 a 7 s |
| 2 | «¿Qué alertas tiene el curso y qué me recomiendas?» | 5 alertas (0 críticas, 2 de atención, 3 informativas), una inferencia y una recomendación | 3 de 3 correctas, 19 a 26 s |
| 3 | «¿Cuál es el progreso de mis estudiantes?» | Indicadores del curso, una inferencia y una recomendación | 3 de 3 correctas, 16 a 20 s |
| 4 | «Genera un informe del curso PRUEBA01» | Informe con período de las observaciones, indicadores y cada alerta con estudiante, valor observado y umbral | 3 de 3 correctas, 7 a 9 s |
| 5 | Falla simulada (ver sección 5) | El agente avisa que no pudo obtener el dato y no inventa nada | 3 de 3 correctas, 13 a 14 s |

La primera pregunta después de encender el modelo es la más lenta (puede tardar hasta unos 45 segundos). Conviene hacer una pregunta de calentamiento antes de empezar, por ejemplo «¿Qué cursos tengo?».

## 5. Simular una falla en la demostración

Para mostrar que el agente no inventa datos cuando falla un servicio, se detiene analytics y se hace una pregunta de alertas:

```powershell
docker stop edumonitor-analytics
```

Pregunta: «¿Qué alertas tiene el curso y qué me recomiendas?». El agente responde: «No pude obtener el dato porque Moodle o un servicio no respondió; reintenta o sincroniza el curso», sin ninguna cifra.

Para volver a la normalidad:

```powershell
docker start edumonitor-analytics
```

Se vuelve a preguntar después de unos segundos.

## 6. Antes de la demostración

1. Docker Desktop encendido y los servicios arriba (`docker compose up -d`); el gateway, auth-courses, moodle-sync y analytics deben estar sanos (`docker ps`).
2. El curso sincronizado: en «Mis cursos», pulsar «Sincronizar» y esperar el estado «Actualizado».
3. Ollama encendido y el modelo descargado: `ollama list` debe mostrar `qwen3:1.7b`. Si falta: `ollama pull qwen3:1.7b`.
4. El agente en marcha: http://localhost:5004/health debe devolver `"status":"ok"` y `"modelAvailable":true`.
5. Cerrar programas que consuman memoria (navegadores con muchas pestañas): con poca memoria libre, las respuestas pasan de unos 10 segundos a más de un minuto.
6. Hacer una pregunta de calentamiento y confirmar que responde.

## 7. Si algo falla

| Lo que se ve | Causa probable | Qué hacer |
|---|---|---|
| «No pude consultar al modelo de lenguaje» | Ollama sin el modelo o apagado | `ollama list`; si falta, `ollama pull qwen3:1.7b` |
| «No pude obtener el dato porque Moodle o un servicio no respondió» | Un servicio del Compose está detenido | `docker ps`; levantar el servicio caído |
| «El curso aún no tiene datos sincronizados» | El curso no se ha sincronizado | Pulsar «Sincronizar» en «Mis cursos» |
| «No encontré un curso llamado …» | El nombre escrito no es un curso del docente | Elegir el curso en el selector o escribir su código |
| La respuesta tarda más de un minuto | Poca memoria libre o modelo frío | Cerrar programas y repetir la pregunta |
| El chat dice que la sesión venció | El token de acceso expiró (60 minutos) | Iniciar sesión de nuevo |

## 8. Evidencia de calidad

- **Evaluación final:** los 21 escenarios se aprobaron, con 2 de 2 accesos no autorizados rechazados, 5 de 5 fallas sin datos inventados y el 100 % de las cifras citadas con respaldo en los datos. Ver `evaluation/agent-scenarios/reportes/REPORTE-EVALUACION-FINAL.md`.
- **Pruebas automáticas:** 272 pruebas del agente, con una cobertura del 96 % (`pytest --cov=app` desde `services/agent-service`); el requisito RNF-08 pide al menos el 70 %.
- **Diseño:** `docs/agent-design/diseno-agente.md` describe los contratos de las herramientas, el flujo del agente y el formato de las trazas.
