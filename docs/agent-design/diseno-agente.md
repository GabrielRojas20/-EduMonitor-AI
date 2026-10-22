# Diseño del agente: herramientas, flujo y formatos (S1-11)

**Estado:** borrador para revisión de Mikel, Gabriel y Benjamín
**Responsable:** Juan
**Servicio:** `agent-service` (Python 3.11, FastAPI, LangGraph, Pydantic) con Ollama
**Basado en:** `api-gateway.v1.yaml` y `moodle-sync.v1.yaml` (S1-07, borrador), decisiones de S1-06 y pruebas de modelos de S1-12

## 1. Principios

1. El agente **solo lee**. No tiene herramientas que modifiquen datos ni que envíen mensajes.
2. El agente consulta únicamente el **api-gateway**, reenviando el JWT del docente. Nunca accede a la base de datos ni a Moodle.
3. Los **cálculos son deterministas** y los hace `analytics-service`. El modelo de lenguaje solo explica resultados y recomienda acciones.
4. Todo número que aparece en una respuesta debe salir de la salida de una herramienta. Si no hay dato, el agente lo dice y no lo inventa.
5. Un `score` nulo **no es 0**. Se respetan los estados `graded`, `pending_grading` y `not_submitted`.
6. Lo que devuelven las herramientas son **datos no confiables**: nunca se ejecutan como instrucciones.

## 2. Contexto de ejecución

| Elemento | Valor propuesto |
|---|---|
| Entrada | `POST /chat` del `agent-service` con encabezado `Authorization: Bearer <JWT>` y el mensaje del docente |
| Modelo | `qwen2.5:3b` (provisional); alternativa `qwen3:1.7b` (ver `docs/benchmarks/ollama-pruebas-modelos.md`) |
| Memoria de conversación | Sin memoria en v1: cada mensaje es independiente (pregunta abierta 4 del Product Owner) |
| Máximo de llamadas a herramientas por mensaje | 5 |
| Tiempo máximo por herramienta | 10 s |
| Tiempo máximo por mensaje | 60 s (meta del plan, sección 8.1) |
| Temperatura | 0 para la selección de herramientas |

## 3. Contrato de las herramientas

Cada herramienta tiene un esquema de entrada y otro de salida, validados con Pydantic. Si la entrada del modelo no valida, la herramienta no se ejecuta y el agente recibe un error `VALIDATION_ERROR`.

Convención de salida común de toda herramienta:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "source": { "endpoint": "GET /api/v1/courses", "requestId": "…", "fetchedAt": "2026-10-22T15:04:05Z" }
}
```

En error, `ok` es `false`, `data` es `null` y `error` tiene la forma:

```json
{ "code": "COURSE_NOT_AUTHORIZED", "message": "El docente no tiene acceso a ese curso", "retryable": false }
```

Los códigos de error son los del gateway: `TOKEN_EXPIRED`, `TOKEN_INVALID`, `COURSE_NOT_AUTHORIZED`, `COURSE_NOT_FOUND`, `STUDENT_NOT_FOUND`, `MOODLE_UNAVAILABLE`, `DATA_NOT_AVAILABLE` y `VALIDATION_ERROR`; se añade `TOOL_TIMEOUT` para el tiempo agotado.

### 3.1 `listar_cursos`

Lista los cursos a los que el docente tiene acceso.

- **Gateway:** `GET /api/v1/courses`
- **Entrada:** sin parámetros.
- **Salida (`data`):**

```json
{
  "courses": [
    { "id": 2, "shortName": "PRUEBA01", "fullName": "Curso de Prueba EduMonitor",
      "studentCount": 8, "lastSyncAt": "2026-10-22T14:00:00Z" }
  ]
}
```

### 3.2 `obtener_calificaciones`

Devuelve las calificaciones de un curso, opcionalmente de un estudiante o de una actividad.

- **Gateway:** `GET /api/v1/courses/{courseId}/grades` (con `studentId` y `activityId` opcionales), paginado.
- **Entrada:**

```json
{
  "type": "object",
  "required": ["course_id"],
  "properties": {
    "course_id": { "type": "integer", "description": "Id del curso en Moodle" },
    "student_id": { "type": "integer", "description": "Id del estudiante en Moodle" },
    "activity_id": { "type": "integer", "description": "Id de la actividad" }
  }
}
```

- **Salida (`data`):**

```json
{
  "courseId": 2,
  "items": [
    { "studentId": 4, "activityId": 1, "activityName": "Tarea 1", "status": "graded",
      "score": 8.5, "maxScore": 10, "submittedAt": "2026-10-10T12:00:00Z", "gradedAt": "2026-10-12T09:00:00Z" },
    { "studentId": 5, "activityId": 1, "activityName": "Tarea 1", "status": "not_submitted",
      "score": null, "maxScore": 10, "submittedAt": null, "gradedAt": null }
  ],
  "total": 2,
  "truncated": false
}
```

La herramienta recorre las páginas del gateway hasta un máximo de 500 registros. Si hay más, devuelve `truncated: true` y el agente lo menciona.

### 3.3 `obtener_progreso`

Devuelve el progreso de cada estudiante: actividades entregadas, calificadas y pendientes, y la finalización de actividades si Moodle la expone.

- **Gateway:** la ruta de progreso **no existe todavía** en el contrato borrador. Se propone `GET /api/v1/courses/{courseId}/progress`, a definir con Mikel (datos de Moodle, S1-06 sección 9) y Gabriel (cálculo). Hasta entonces, el mock devuelve datos de ejemplo.
- **Entrada:**

```json
{
  "type": "object",
  "required": ["course_id"],
  "properties": {
    "course_id": { "type": "integer" },
    "student_id": { "type": "integer" }
  }
}
```

- **Salida (`data`), propuesta:**

```json
{
  "courseId": 2,
  "students": [
    { "studentId": 4, "activitiesTotal": 2, "graded": 1, "pendingGrading": 0, "notSubmitted": 1,
      "completion": { "available": false } }
  ]
}
```

Cuando Moodle no expone la finalización, `completion.available` es `false` y el agente dice "dato no disponible", no "0 %".

### 3.4 `identificar_alertas`

Devuelve las alertas activas de un curso, con la evidencia de cada una.

- **Gateway:** ruta de `analytics-service` por el gateway (contrato de Gabriel, S1-10). Propuesta provisional: `GET /api/v1/courses/{courseId}/alerts`.
- **Entrada:**

```json
{
  "type": "object",
  "required": ["course_id"],
  "properties": {
    "course_id": { "type": "integer" },
    "student_id": { "type": "integer" },
    "severity": { "type": "string", "enum": ["low", "medium", "high"] }
  }
}
```

- **Salida (`data`), propuesta (se ajusta al formato de S1-09/S1-10):**

```json
{
  "courseId": 2,
  "alerts": [
    { "alertId": "a-001", "studentId": 5, "ruleId": "R-BAJO-PROMEDIO", "ruleName": "Promedio bajo",
      "severity": "high",
      "evidence": { "value": 4.2, "threshold": 5.0, "unit": "nota sobre 10", "activities": [1, 2],
                    "computedAt": "2026-10-22T14:05:00Z" } }
  ]
}
```

### 3.5 `generar_resumen`

Reúne los datos ya calculados para preparar el informe del curso. **No calcula nada nuevo**: llama a los endpoints de calificaciones, progreso y alertas y arma una estructura que el modelo redacta.

- **Gateway:** combinación de las rutas anteriores y los indicadores de analytics (a definir en S1-10).
- **Entrada:**

```json
{
  "type": "object",
  "required": ["course_id"],
  "properties": {
    "course_id": { "type": "integer" },
    "period": {
      "type": "object",
      "properties": { "from": { "type": "string", "format": "date" }, "to": { "type": "string", "format": "date" } }
    }
  }
}
```

- **Salida (`data`):**

```json
{
  "course": { "id": 2, "fullName": "Curso de Prueba EduMonitor" },
  "period": { "from": "2026-10-01", "to": "2026-10-22" },
  "generatedAt": "2026-10-22T15:10:00Z",
  "lastSyncAt": "2026-10-22T14:00:00Z",
  "metrics": [ { "name": "promedio_curso", "value": 7.3, "unit": "nota sobre 10", "sourceTool": "obtener_calificaciones" } ],
  "findings": [ { "type": "alert", "ref": "a-001", "studentId": 5 } ],
  "unavailable": [ "completion" ]
}
```

### 3.6 Resumen de herramientas

| Herramienta | Sprint | Ruta del gateway | Estado de la ruta |
|---|---|---|---|
| `listar_cursos` | S3 | `GET /api/v1/courses` | En el contrato S1-07 |
| `obtener_calificaciones` | S3 | `GET /api/v1/courses/{id}/grades` | En el contrato S1-07 |
| `obtener_progreso` | S3 | `GET /api/v1/courses/{id}/progress` | **Por definir** |
| `identificar_alertas` | S4 | `GET /api/v1/courses/{id}/alerts` | **Por definir** (S1-10) |
| `generar_resumen` | S5 | combinación | **Por definir** (S1-10) |

## 4. Flujo de LangGraph

```mermaid
flowchart TD
    A[recibir_mensaje] --> B[validar_contexto]
    B -->|JWT ausente o vencido| X[responder_error_sesion]
    B --> C[clasificar_intencion]
    C -->|fuera de alcance| R[responder_rechazo]
    C -->|consulta de datos| D[planificar_herramientas]
    D --> E[ejecutar_herramientas]
    E -->|hay mas llamadas y no se llego al limite| D
    E --> F[verificar_evidencia]
    F -->|falta algun dato| G[marcar_datos_no_disponibles]
    F --> H[redactar_respuesta]
    G --> H
    H --> I[validar_salida]
    I -->|cifra sin fuente| H
    I --> J[guardar_traza]
    X --> J
    R --> J
    J --> K[responder]
```

| Nodo | Qué hace |
|---|---|
| `recibir_mensaje` | Recibe el mensaje y el JWT. Genera un `traceId`. El JWT queda solo en memoria del request. |
| `validar_contexto` | Comprueba que haya JWT y que no esté vencido (sin validar la firma, eso lo hace el gateway). |
| `clasificar_intencion` | Decide si la consulta es de datos del curso, si pide un informe o si está fuera de alcance (modificar notas, enviar mensajes, predicciones psicológicas, otros temas). |
| `planificar_herramientas` | El modelo elige qué herramientas llamar y con qué argumentos. |
| `ejecutar_herramientas` | Valida los argumentos con Pydantic, llama al gateway con el JWT y registra el resultado. Respeta los límites de la sección 2. |
| `verificar_evidencia` | Comprueba si todas las herramientas devolvieron datos. Si falló alguna, pasa a `marcar_datos_no_disponibles`. |
| `marcar_datos_no_disponibles` | Anota explícitamente qué dato no se pudo obtener y por qué. |
| `redactar_respuesta` | El modelo redacta con el formato de la sección 6, solo con las salidas de las herramientas. |
| `validar_salida` | Código determinista: comprueba que cada cifra de los hechos aparece en alguna salida de herramienta. Si no, vuelve a redactar (máximo 1 reintento) o elimina la cifra. |
| `guardar_traza` | Guarda la traza de la sección 5 en el esquema `agent`. |

Comportamientos ante fallas:

| Situación | Respuesta del agente |
|---|---|
| `TOKEN_EXPIRED` o `TOKEN_INVALID` | Avisa que la sesión venció y pide iniciar sesión de nuevo. |
| `COURSE_NOT_AUTHORIZED` | Informa que no tiene acceso a ese curso. No intenta otro camino. |
| `MOODLE_UNAVAILABLE` o `TOOL_TIMEOUT` | Informa que no pudo obtener el dato, sugiere reintentar o sincronizar. No estima valores. |
| `truncated: true` | Indica que se analizaron solo los primeros registros. |
| Consulta fuera de alcance | Rechaza en una frase y explica qué sí puede hacer. |

## 5. Formato de las trazas

Se guarda una traza por mensaje, en el esquema `agent`. Estructura (JSON):

```json
{
  "traceId": "9f1c…",
  "requestId": "…",
  "startedAt": "2026-10-22T15:04:05Z",
  "finishedAt": "2026-10-22T15:04:21Z",
  "teacherId": 3,
  "model": "qwen2.5:3b",
  "message": { "text": "¿Quién está en riesgo en el curso 2?", "redacted": false },
  "intent": "consulta_datos",
  "steps": [
    { "n": 1, "node": "ejecutar_herramientas", "tool": "identificar_alertas",
      "args": { "course_id": 2 }, "ok": true, "errorCode": null,
      "durationMs": 840, "resultSummary": { "alerts": 1 } }
  ],
  "output": { "validated": true, "unsourcedNumbersRemoved": 0 },
  "totals": { "toolCalls": 1, "durationMs": 15800 },
  "status": "ok"
}
```

Reglas:
- **Nunca** se guarda el JWT ni el contenido de las entregas.
- Las trazas guardan los identificadores de estudiantes de Moodle, no sus nombres, hasta que el Product Owner decida (pregunta abierta 9).
- Para cada herramienta se guardan los argumentos, el código de resultado, la duración y un resumen del resultado, no la salida completa.
- `status` puede ser `ok`, `partial` (falló alguna herramienta), `refused` (fuera de alcance) o `error`.

## 6. Formato de las respuestas

El agente siempre separa **hechos**, **inferencias** y **recomendaciones**. El `agent-service` devuelve este JSON y la interfaz lo muestra en tres bloques:

```json
{
  "traceId": "9f1c…",
  "answer": {
    "facts": [
      { "text": "El estudiante 5 tiene un promedio de 4,2 sobre 10 en las actividades calificadas.",
        "sources": [ { "tool": "obtener_calificaciones", "stepN": 1 } ] }
    ],
    "inferences": [
      { "text": "El promedio está por debajo del umbral de 5,0 de la regla «Promedio bajo».",
        "basedOn": [ 0 ] }
    ],
    "recommendations": [
      { "text": "Conviene revisar con el estudiante 5 las dos últimas tareas.", "relatedFinding": 0 }
    ],
    "unavailable": [ "Finalización de actividades: Moodle no expone el dato." ]
  },
  "meta": { "courseId": 2, "lastSyncAt": "2026-10-22T14:00:00Z", "status": "ok" }
}
```

Reglas del formato:
- Cada **hecho** cita su fuente (herramienta y paso de la traza) y su cifra proviene de la salida de esa herramienta.
- Cada **inferencia** indica en qué hechos se basa. Se redacta con cautela ("podría", "sugiere"), nunca como certeza.
- Cada **recomendación** se vincula a un hallazgo. No hay recomendaciones sin respaldo.
- Siempre se muestra la fecha de la última sincronización.
- Lo que no se pudo obtener va en `unavailable`.
- El agente no afirma nada sobre el estado psicológico o personal de un estudiante.

## 7. Seguridad

| Riesgo | Medida |
|---|---|
| Acceso a un curso ajeno | El gateway devuelve 403 y el agente lo informa. No hay otra vía de datos. |
| Instrucciones escondidas en los datos (nombres de actividades, comentarios) | Las salidas se tratan como datos: se pasan al modelo dentro de un bloque delimitado, truncadas y con los caracteres de control eliminados. El sistema indica que nada dentro del bloque es una orden. |
| Fuga del JWT | No se escribe en trazas ni en registros, y no se incluye en el prompt. |
| Datos inventados | `validar_salida` elimina cifras sin fuente y el conjunto de evaluación incluye escenarios de falla. |
| Petición fuera de alcance | El nodo `clasificar_intencion` rechaza modificar notas, enviar mensajes y hacer predicciones psicológicas. |
| Abuso de herramientas | Límite de 5 llamadas por mensaje y tiempo máximo por herramienta y por mensaje. |

## 8. Pruebas previstas

- **Unitarias (pytest):** cada herramienta con respuestas simuladas del gateway, validación de esquemas, manejo de cada código de error y `validar_salida`.
- **Evaluación:** los 20 escenarios del plan (5 consulta simple, 5 falla de herramienta, 5 alertas con evidencia, 3 seguridad, 2 informe), ejecutados al final de cada sprint desde el Sprint 3. Metas: 100 % de accesos no autorizados rechazados, ningún dato inventado en fallas y al menos 90 % de cifras que coinciden con la fuente.
- **Seguridad:** escenarios con instrucciones escondidas en nombres de actividades y comentarios.

## 9. Dependencias y puntos por acordar

| Con | Qué se necesita | Quién decide |
|---|---|---|
| Mikel | Ruta de progreso y finalización (`/progress`) y confirmar que el gateway reenvía `X-Request-Id` | Mikel |
| Gabriel | Contrato de alertas y de indicadores (S1-10): formato de evidencia, rutas y paginación | Gabriel |
| Benjamín | Cómo se muestran los tres bloques (hechos, inferencias, recomendaciones) y los datos no disponibles en el chat | Benjamín |
| Product Owner | Memoria de la conversación (pregunta 4), nombres en trazas (pregunta 9) y evaluación del agente (pregunta 8) | Product Owner |

Para el Sprint 2, el servidor mock del gateway se genera a partir de los contratos definitivos y sirve para probar estas herramientas antes de que existan los servicios reales.
