# Documento de requisitos de EduMonitor AI (S1-03)

**Estado:** borrador para el Product Owner
**Responsable:** Juan (requisitos de interfaz: Benjamín)
**Fuente:** Planificación del proyecto, secciones 1, 6, 8 y 11

## 1. Propósito y alcance

EduMonitor AI es una aplicación web, independiente de Moodle, que ayuda al docente a dar seguimiento al rendimiento académico de sus cursos. Consulta Moodle mediante servicios web autorizados, calcula indicadores que se pueden verificar y usa un agente de inteligencia artificial para interpretarlos y sugerir acciones pedagógicas. El sistema apoya el criterio del docente: no lo reemplaza ni modifica calificaciones.

### 1.1 Dentro del alcance (producto mínimo)

1. Autenticación del docente y acceso a los cursos que tiene autorizados.
2. Sincronización manual con Moodle.
3. Dashboard de curso, ficha individual por estudiante e indicadores.
4. Alertas académicas explicables, con reglas configurables.
5. Chat con un agente de IA que usa al menos tres herramientas reales, y generación de un informe del curso.

### 1.2 Fuera del alcance

- Predicción clínica o psicológica de estudiantes.
- Modificación de notas en Moodle.
- Envío automático de mensajes a estudiantes.
- Entrenamiento de modelos propios y sistemas con varios agentes.

## 2. Actores

| Actor | Descripción |
|---|---|
| Docente | Inicia sesión, consulta sus cursos, sincroniza, revisa indicadores y alertas, y conversa con el agente. |
| Administrador | Rol previsto en el JWT. Sus permisos sobre los cursos están por definir (ver preguntas abiertas). |
| Product Owner | Ingeniero de la materia. Prioriza el backlog y acepta o rechaza lo entregado en cada sprint. |

## 3. Requisitos funcionales

Cada requisito tiene un criterio que se puede comprobar con una prueba, una medición o una evidencia en el repositorio.

| ID | Requisito | Criterio verificable |
|---|---|---|
| RF-01 | El docente puede iniciar sesión con correo y contraseña. | Con credenciales válidas se devuelve un JWT; con credenciales inválidas se devuelve 401 con código `INVALID_CREDENTIALS`. |
| RF-02 | El docente solo accede a los cursos que tiene autorizados. | El listado de cursos devuelve solo los suyos. Pedir un curso ajeno devuelve 403, y esto está cubierto por una prueba automática. |
| RF-03 | La sesión expira. | Un JWT vencido es rechazado con 401 `TOKEN_EXPIRED`. Duración propuesta: 60 minutos. |
| RF-04 | El docente puede sincronizar manualmente un curso con Moodle. | `POST /courses/{id}/sync` responde 202 y el estado de la sincronización se puede consultar con su fecha. |
| RF-05 | El sistema distingue nota cero, sin entrega y pendiente de calificar. | Cada calificación tiene el estado `graded`, `pending_grading` o `not_submitted`. Una nota de 0 se guarda como `graded` con puntaje 0. Un borrador cuenta como sin entrega. |
| RF-06 | Si Moodle no expone un dato, el sistema lo informa como no disponible. | En lugar de un valor inventado o un 0, la respuesta indica que el dato no está disponible. |
| RF-07 | El sistema no guarda el contenido de las entregas de los estudiantes. | Los datos sincronizados contienen solo identificador, estado, estado de calificación y fechas. No existe el campo `onlinetext` en la base de datos. |
| RF-08 | El docente ve un dashboard de curso. | El dashboard muestra los indicadores del curso y carga en 3 segundos o menos con el tamaño de referencia (ver RNF-01). |
| RF-09 | El docente ve una ficha individual por estudiante. | La ficha muestra las calificaciones y el progreso del estudiante, y sus valores coinciden con los de la fuente. |
| RF-10 | Los indicadores se calculan de forma determinista. | Cada fórmula está documentada con ejemplos, el cálculo se hace en `analytics-service` y tiene pruebas unitarias. |
| RF-11 | El sistema genera alertas académicas con reglas configurables. | Los umbrales de las reglas se pueden cambiar sin modificar el código y el cambio altera las alertas generadas. |
| RF-12 | Cada alerta se explica por sí sola. | La alerta muestra la regla aplicada, el valor que la activó y la fecha. |
| RF-13 | El docente conversa con un agente de IA. | El chat responde preguntas sobre los cursos autorizados del docente. |
| RF-14 | El agente usa al menos tres herramientas reales. | Al menos tres de `listar_cursos`, `obtener_calificaciones`, `obtener_progreso`, `identificar_alertas` y `generar_resumen` funcionan contra el gateway. |
| RF-15 | El agente consulta los datos solo a través del gateway con el token del docente. | El agente no tiene acceso a la base de datos ni a Moodle. Una consulta a un curso no autorizado es rechazada. |
| RF-16 | Las respuestas del agente separan hechos, inferencias y recomendaciones. | Cada respuesta incluye las tres secciones, y las recomendaciones se relacionan con un hallazgo. |
| RF-17 | El sistema guarda trazas del agente. | Cada consulta deja una traza con las herramientas llamadas y sus resultados en el esquema `agent`. |
| RF-18 | El docente obtiene un informe del curso. | El informe incluye período, métricas, hallazgos y fecha. |
| RF-19 | Las sincronizaciones quedan auditadas. | Cada sincronización registra quién la lanzó, cuándo y con qué resultado. |

## 4. Requisitos no funcionales

| ID | Requisito | Criterio verificable |
|---|---|---|
| RNF-01 | Rendimiento. | Referencia: un docente, tres cursos y 50 estudiantes por curso. Primera respuesta del chat en 10 s o menos; respuesta completa en 60 s o menos; sincronización de un curso de 50 estudiantes en 2 minutos o menos; dashboard en 3 s o menos. Se mide en S1-12 y se repite en el Sprint 5. |
| RNF-02 | Privacidad de los datos. | El modelo corre en local (Ollama) y no se envían datos de estudiantes a servicios externos. No hay datos reales en el repositorio. |
| RNF-03 | Seguridad de secretos. | El repositorio solo contiene `.env.example`. El CI falla si hay un `.env` versionado. |
| RNF-04 | Seguridad de acceso. | La autorización por curso y la expiración del JWT tienen pruebas automáticas. Se refuerzan JWT, CORS y secretos en el Sprint 4. |
| RNF-05 | Resistencia del agente a instrucciones escondidas. | El agente ignora instrucciones dentro de los datos que lee (por ejemplo, el nombre de una actividad) en los escenarios de seguridad. |
| RNF-06 | Fiabilidad del agente. | Rechaza el 100 % de los accesos no autorizados, no inventa datos en ningún escenario de falla, y al menos el 90 % de las cifras que cita coincide con la fuente. |
| RNF-07 | Solo lectura sobre Moodle. | Ninguna llamada del sistema modifica datos en Moodle. |
| RNF-08 | Calidad del código. | Cobertura mínima del 70 % en `analytics-service` y `agent-service`. Cada PR ejecuta pruebas y linters y no se une si fallan. |
| RNF-09 | Contratos de API. | Los contratos OpenAPI están versionados (v1, v2) y definitivos el D4 del Sprint 1. Quitar o renombrar campos exige una versión nueva. |
| RNF-10 | Ejecución reproducible. | Con `docker-compose` el proyecto se levanta en la máquina de cada integrante. |
| RNF-11 | Trazabilidad de los datos. | Cada dato mostrado puede rastrearse hasta su origen en Moodle y a la fecha de sincronización. |

## 5. Requisitos de interfaz (completa: Benjamín)

> **Pendiente de Benjamín.** Cada pantalla debe tener requisitos con un criterio verificable. Se dejan la estructura y las preguntas guía.

| ID | Pantalla | Requisitos de interfaz | Criterio verificable |
|---|---|---|---|
| RI-01 | Login | _Por completar_ | _Por completar_ |
| RI-02 | Lista de cursos | _Por completar_ | _Por completar_ |
| RI-03 | Dashboard de curso | _Por completar_ | _Por completar_ |
| RI-04 | Ficha individual del estudiante | _Por completar_ | _Por completar_ |
| RI-05 | Alertas con sus evidencias | _Por completar_ | _Por completar_ |
| RI-06 | Chat con el agente | _Por completar_ | _Por completar_ |
| RI-07 | Informe de curso | _Por completar_ | _Por completar_ |
| RI-08 | Estados vacíos y de error | _Por completar_ | _Por completar_ |

Preguntas guía para cada pantalla:
- ¿Qué datos o campos muestra y cuáles son obligatorios?
- ¿Qué pasa cuando no hay datos, hay un error o Moodle no está disponible?
- ¿Qué muestra el chat cuando el agente tarda o falla una herramienta?
- ¿Cómo se muestra "dato no disponible" frente a un 0?
- ¿Qué se necesita de Juan (chat) y de Gabriel (alertas) para cada pantalla?

## 6. Matriz de cumplimiento inicial

Se actualiza en la revisión de cada sprint.

| ID | Sprint | Responsable | Estado |
|---|---|---|---|
| RF-01 | S2 | Mikel | Pendiente |
| RF-02 | S2 | Mikel | Pendiente |
| RF-03 | S2 | Mikel | Pendiente |
| RF-04 | S2 | Mikel | Contrato en borrador (S1-07) |
| RF-05 | S2 | Mikel y Gabriel | Evidencia en S1-06; contrato en borrador (S1-07) |
| RF-06 | S3 | Mikel y Gabriel | Pendiente |
| RF-07 | S2 | Mikel | Decisión registrada en S1-06 |
| RF-08 | S3 | Benjamín y Gabriel | Pendiente |
| RF-09 | S3 | Benjamín y Gabriel | Pendiente |
| RF-10 | S3 | Gabriel | Pendiente |
| RF-11 | S4 | Gabriel | Pendiente |
| RF-12 | S4 | Gabriel y Benjamín | Pendiente |
| RF-13 | S4 a S5 | Juan y Benjamín | Pendiente |
| RF-14 | S3 a S5 | Juan | Pendiente |
| RF-15 | S3 | Juan y Mikel | Pendiente |
| RF-16 | S4 a S5 | Juan | Pendiente |
| RF-17 | S3 a S4 | Juan | Pendiente |
| RF-18 | S5 | Gabriel y Benjamín | Pendiente |
| RF-19 | S4 | Mikel | Pendiente |
| RNF-01 | S1 y S5 | Todos | Medido parcialmente para el modelo local (S1-12) |
| RNF-02 | S1 a S6 | Todos | Pendiente |
| RNF-03 | S1 | Gabriel | CI con chequeo de `.env` |
| RNF-04 | S4 | Mikel | Pendiente |
| RNF-05 | S4 a S6 | Juan | Pendiente |
| RNF-06 | S3 a S6 | Juan | Pendiente |
| RNF-07 | S2 | Mikel | Pendiente |
| RNF-08 | S2 a S6 | Gabriel | Pendiente |
| RNF-09 | S1 | Mikel y Gabriel | Borradores en revisión |
| RNF-10 | S2 | Gabriel | Pendiente |
| RNF-11 | S3 | Gabriel y Mikel | Pendiente |

Los requisitos de interfaz (RI-01 a RI-08) se agregan a la matriz cuando Benjamín los complete.

## 7. Supuestos y restricciones

- Se usa Moodle 5.2.4 en Docker, con datos ficticios.
- Hay cinco servicios: `api-gateway`, `auth-courses`, `moodle-sync`, `analytics` y `agent-service`, con una sola instancia de SQL Server y un esquema por servicio.
- Las metas de rendimiento y de evaluación del agente son propuestas hasta que el Product Owner las apruebe.
- El modelo local se eligió de forma provisional en S1-12 (`qwen2.5:3b`) y se confirma con los escenarios de evaluación.

## 8. Preguntas abiertas para el Product Owner

1. ¿Qué consultas reales hará un docente en el chat? Se necesitan entre cinco y diez ejemplos para el conjunto de evaluación del agente.
2. ¿Qué debe contener exactamente el informe de curso (secciones, período y formato)?
3. ¿Qué formato y nivel de detalle se esperan en las recomendaciones pedagógicas?
4. ¿El agente debe recordar el contexto de la conversación o basta con que responda preguntas independientes?
5. ¿Le parecen razonables las metas de rendimiento de RNF-01, por ejemplo una respuesta completa en un máximo de 60 segundos?
6. ¿Se permite usar un modelo en la nube como plan B si el hardware no alcanza, siempre sin datos identificables?
7. ¿Con qué equipo se hará la demostración final?
8. ¿Cómo se evaluará al agente (escenarios definidos o preguntas libres en vivo) y qué significa exactamente "no inventar datos"?
9. ¿Las trazas del agente pueden guardar nombres de estudiantes o deben anonimizarse?
10. ¿Son adecuados los umbrales iniciales de las reglas de alerta definidos en S1-09?

Pregunta adicional surgida en S1-07: ¿Debe contemplarse el inicio de sesión institucional con Microsoft en una versión posterior? ¿Qué puede ver el rol administrador?
