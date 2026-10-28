# Revisión cruzada de contratos OpenAPI (S1-14)

**Revisor:** Juan (consumidor de los contratos desde `agent-service`)
**Fecha:** 2026-10-25
**Contratos revisados:** los que están unidos a `develop` (PRs #2, #6 y #7)

| Contrato | Autor | Versión declarada | Resultado |
|---|---|---|---|
| `api-gateway.v1.yaml` | Mikel | 1.0.0 | Aprobado con observaciones |
| `auth-courses.v1.yaml` | Mikel | 1.0.0 | Aprobado con observaciones |
| `moodle-sync.v1.yaml` | Mikel | 1.0.0 | Aprobado con observaciones |
| `analytics.v1.yaml` | Gabriel | 1.0.0 | Observaciones O-12 a O-20 resueltas en esta PR |

Ninguna observación bloquea el diseño del agente. Las marcadas como **Alta** conviene resolverlas antes de congelar los contratos y de generar el mock del gateway (Sprint 2, día 1).

## 1. Qué se revisó y cómo

- Lectura completa de los cuatro contratos y de las reglas iniciales de analytics (`docs/analytics-rules/reglas-iniciales.md`).
- Comparación con la evidencia de Moodle (S1-06), con las decisiones registradas en el documento de requisitos y con el uso que hará el agente de cada ruta (`docs/agent-design/diseno-agente.md`, en revisión en el PR #5).
- Coherencia entre contratos: nombres de campos, códigos de error, puertos y rutas.

Es una revisión estática: no se levantó ningún servicio ni se validaron los archivos con un linter de OpenAPI. Conviene que el CI de Sprint 2 valide los YAML.

## 2. Qué está bien

- El flujo del token del docente hasta el agente está descrito de punta a punta y coincide con el diseño del agente (JWT reenviado, sin credenciales propias, `TOKEN_EXPIRED` como señal de sesión vencida).
- `score` nulo nunca es 0, y los tres estados (`graded`, `pending_grading`, `not_submitted`) están definidos igual en gateway, `moodle-sync` y analytics.
- El PR #7 resolvió bien la representación de datos faltantes: `completionState: not_available` para un dato suelto y `DATA_NOT_AVAILABLE` solo para un recurso completo. `submissionStatus` permite tratar el borrador sin cambiar el contrato.
- El formato de error común (RFC 7807 con `code` estable) y la paginación (`page`, `pageSize` de 1 a 200) son iguales en todos los servicios.
- Analytics devuelve evidencia en cada alerta (métrica, valor, umbral, explicación y fuentes) y la calidad del dato (`status` y `dataQuality`), lo que cumple RF-12 y RF-06.
- `onlinetext` no aparece en ningún esquema (RF-07).

## 3. Estado de las observaciones hechas en las revisiones anteriores (PRs #1 y #2)

| Observación anterior | Estado |
|---|---|
| `DATA_NOT_AVAILABLE` definido pero sin uso | **Resuelta** en el PR #7 (semántica y `completionState`). |
| Falta el contrato de analytics | **Resuelta** en el PR #6. |
| El 401 de login describe un token vencido | **Parcial**: la descripción ya menciona `INVALID_CREDENTIALS`, pero sigue siendo genérica (ver O-11). |
| El estado de nota solo cubre tareas (`mod_assign_*`) | **Abierta** (O-04). |
| El 503 `MOODLE_UNAVAILABLE` solo está en las rutas de sync | **Abierta** (O-03). |
| Servicios internos alcanzables directamente | **Abierta** (O-07). |
| Puertos sin alinear con docker-compose | **Abierta** (O-06). |
| JWT sin `aud`, sin valor de `iss`, rol `admin` sin reglas | **Abierta** (O-08). |
| El gateway no documenta el mapeo a las rutas internas | **Abierta** (O-01). |
| El correo del estudiante se expone sin regla de privacidad | **Abierta** (O-10). |
| `STUDENT_NOT_FOUND` mencionado en `auth-courses` sin rutas de estudiante | **Abierta** (O-09). |

## 4. Observaciones

Severidad: **Alta** afecta a la integración; **Media** puede causar errores o ambigüedad; **Baja** es de claridad.

### 4.1 `api-gateway` y servicios de Mikel

| ID | Sev. | Contrato | Observación | Propuesta | Responsable |
|---|---|---|---|---|---|
| O-01 | Alta | gateway | El gateway no lista las rutas de analytics (`/analytics`, `/analytics/students/{id}`, `/analytics/alerts`, `/analytics/report`); solo dice que "también salen por este gateway". El agente necesita esas rutas en el contrato del gateway, y el mock se genera a partir de él. Tampoco documenta cómo se mapean sus rutas `/api/v1/...` a las de cada servicio interno ni la llamada previa a `/internal/courses/{courseId}/access`. | Agregar las rutas de analytics al gateway con los mismos parámetros y esquemas, y una nota con el mapeo a servicios internos. | Mikel |
| O-02 | Media | gateway | Las rutas de lectura (`/students`, `/students/{id}`, `/grades`) no declaran `503`, aunque el PR #7 dice que `DATA_NOT_AVAILABLE` se devuelve cuando no se puede obtener el recurso, por ejemplo porque el curso aún no se sincronizó. Hoy esa respuesta solo está documentada en `POST /sync`. | Declarar `503` (`MOODLE_UNAVAILABLE` o `DATA_NOT_AVAILABLE`) en las rutas de lectura del gateway y de `moodle-sync`. Definir qué responde un curso sin sincronizar. | Mikel |
| O-03 | Media | gateway, moodle-sync | Idem O-02 para `moodle-sync`: solo `POST /sync` declara `409` y `503`. | Ver O-02. | Mikel |
| O-04 | Media | moodle-sync | La normalización del estado se basa solo en `mod_assign_*`. Una actividad calificada que no es tarea (quiz, foro) aparecería como `not_submitted`. `GradeEntry` no indica el tipo de actividad (`ActivityProgress` sí tiene `activityType`). | Decidir si el MVP solo cubre tareas y dejarlo escrito, o añadir `activityType` a `GradeEntry` y el tratamiento de otros tipos. | Mikel y Gabriel |
| O-05 | Baja | moodle-sync | La finalización de actividades se consulta con un solo `userid` por llamada, así que sincronizar un curso de 50 estudiantes implica unas 50 llamadas. | Medir el tiempo en el Sprint 2 frente a la meta de 2 minutos (RNF-01) y definir paralelismo o límite. | Mikel |
| O-06 | Media | todos | Puertos: gateway 5000, `auth-courses` 5001 y `moodle-sync` 5002 en los contratos; analytics 5003 en su contrato, pero `.env.example` define `ANALYTICS_URL` en el 5002, que es el de `moodle-sync`. | Fijar una tabla de puertos única (README y `docker-compose`) y corregir `.env.example`. | Gabriel y Mikel |
| O-07 | Media | auth-courses, moodle-sync | Los servicios internos confían en que el gateway ya validó el acceso al curso. Si sus puertos son alcanzables, se salta la autorización. No hay nota de aislamiento de red. | Documentar que solo el gateway publica puerto en `docker-compose` y que los demás están en una red interna. Se refuerza en el Sprint 4. | Mikel y Gabriel |
| O-08 | Media | auth-courses | El JWT no define `aud`, y `iss` no tiene valor en el contrato (`.env.example` ya usa `JWT_ISSUER=edumonitor`). No dice cómo se reparte el secreto HS256 entre los servicios que lo validan ni qué puede hacer el rol `admin` en cada curso. | Fijar `iss`, `aud` y las reglas del rol `admin`, y citar las variables de entorno. | Mikel |
| O-09 | Baja | auth-courses | La respuesta `NotFound` menciona `STUDENT_NOT_FOUND`, pero el servicio no tiene rutas de estudiante. | Quitar el código de esa respuesta. | Mikel |
| O-10 | Baja | gateway | `Student.email` se expone al docente sin una regla de privacidad ni retención. | Decidir si hace falta el correo o definir la regla (ver pregunta de datos reales en los requisitos). | Mikel y Product Owner |
| O-11 | Baja | gateway, auth-courses | El `401` de login reutiliza la respuesta `Unauthorized`, descrita para tokens. | Definir una respuesta propia con `INVALID_CREDENTIALS`. | Mikel |

### 4.2 `analytics`

| ID | Sev. | Observación | Propuesta | Responsable |
|---|---|---|---|---|
| O-12 | Media | `Counts` incluía `draft` sin aclarar su relación con `notSubmitted`. | Resuelto: `notSubmittedCount` incluye borradores y `draftCount` es un subconjunto informativo que no se suma de nuevo. El contrato y `decisiones-s1-10.md` incluyen un ejemplo numérico. | Gabriel |
| O-13 | Media | La ruta de alertas no permitía filtrar por estado. | Resuelto: se agregó `status` con `active` y `resolved`, por defecto `active`. | Gabriel |
| O-14 | Media | Faltaba explicar el modelo de autorización de analytics. | Resuelto: recibe el JWT reenviado por el gateway, que valida el acceso al curso; analytics rechaza tokens ausentes o inválidos y los servicios internos quedan en red privada. | Gabriel |
| O-15 | Media | `CourseReportData.findings` era una lista de textos libres. | Resuelto: cada hallazgo usa `ReportFinding` con `alertId`, `ruleCode`, `studentId`, `metric` y `text`. | Gabriel |
| O-16 | Baja | Los nombres de métricas y conteos no coincidían y `AlertEvidence.metric` era texto libre. | Resuelto: se usan `averageScore10`, `gradedCount`, `pendingGradingCount`, `notSubmittedCount`, `draftCount` y una enumeración de métricas permitidas. | Gabriel |
| O-17 | Baja | Las rutas no declaraban `400` para parámetros inválidos. | Resuelto: las rutas declaran `400 BadRequest` con `VALIDATION_ERROR`. | Gabriel |
| O-18 | Baja | Existía `snapshotId`, pero no un catálogo de snapshots. | Resuelto: si se omite se usa la última sincronización exitosa; el MVP no expone catálogo de snapshots. | Gabriel |
| O-19 | Baja | La configuración de umbrales y la evolución de `ruleCode` necesitaban una regla de compatibilidad. | Resuelto: los umbrales no cambian el contrato; nuevos códigos se agregan de forma compatible y quitar o renombrar requiere nueva versión. | Gabriel |
| O-20 | Baja | El contrato aún estaba en borrador y faltaba alinear la configuración de puerto. | Resuelto: versión `1.0.0`; analytics usa `5003` y `.env.example` queda alineado. | Gabriel |

## 5. Impacto en el agente

| Herramienta | Depende de | Observaciones que la afectan |
|---|---|---|
| `listar_cursos` | `GET /api/v1/courses` | Ninguna. |
| `obtener_calificaciones` | `GET /api/v1/courses/{id}/grades` | O-02, O-04 |
| `obtener_progreso` | analytics y `GET .../students/{id}` | O-01, O-05, O-12 |
| `identificar_alertas` | `GET .../analytics/alerts` | O-01, O-13, O-16 |
| `generar_resumen` | `GET .../analytics/report` | O-01, O-15 |

Con O-01 resuelto, el mock del gateway puede generarse con todas las rutas que usa el agente.

## 6. Conclusión

Los cuatro contratos están bien planteados y son coherentes en lo esencial. Se aprueban con observaciones. Se propone resolver O-01 antes de generar el mock (Sprint 2, día 1) y las observaciones de severidad Media antes del cierre de la revisión del sprint. Las de severidad Baja pueden quedar para el Sprint 2.

Las respuestas de los autores a cada observación se registran en esta tabla o en los comentarios del PR.
