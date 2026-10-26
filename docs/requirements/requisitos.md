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
| Administrador | Rol previsto en el JWT. Sus permisos sobre los cursos y sobre el historial de auditoría están por definir (preguntas 13 y 14). |
| Product Owner | Ingeniero de la materia. Prioriza el backlog y acepta o rechaza lo entregado en cada sprint. |

## 3. Requisitos funcionales

Cada requisito tiene un criterio que se puede comprobar con una prueba, una medición o una evidencia en el repositorio.

| ID | Requisito | Criterio verificable |
|---|---|---|
| RF-01 | El docente puede iniciar sesión con correo y contraseña. | Con credenciales válidas se devuelve un JWT; con credenciales inválidas se devuelve 401 con código `INVALID_CREDENTIALS`. |
| RF-02 | El docente solo accede a los cursos que tiene autorizados. | El listado de cursos devuelve solo los suyos. Pedir un curso ajeno devuelve 403, y esto está cubierto por una prueba automática. |
| RF-03 | La sesión expira. | Un JWT vencido es rechazado con 401 `TOKEN_EXPIRED`. Duración propuesta: 60 minutos. |
| RF-04 | El docente puede sincronizar manualmente un curso con Moodle. | `POST /api/v1/courses/{courseId}/sync` responde 202 y el estado de la sincronización se puede consultar con su fecha en `GET /api/v1/courses/{courseId}/sync`. Si ya hay una sincronización en curso, responde 409 `SYNC_IN_PROGRESS`. |
| RF-05 | El sistema distingue nota cero, sin entrega y pendiente de calificar. | Cada calificación tiene el estado `graded`, `pending_grading` o `not_submitted`. Una nota de 0 se guarda como `graded` con puntaje 0, y un puntaje nulo nunca se cuenta como 0. Una entrega en borrador (`status: draft`, sin nota) no se confunde con una nota 0. **Propuesta pendiente de confirmar:** que un borrador cuente como "no entregado" en los indicadores. En S1-06 solo se documentó que el borrador queda con estado `draft` y nota vacía; la decisión se cierra en S1-09 (reglas de indicadores) con Gabriel y el Product Owner (pregunta 15). |
| RF-06 | Si Moodle no expone un dato, el sistema lo informa como no disponible. | El dato ausente se representa de forma explícita y nunca como 0 ni como un valor inventado. El mecanismo exacto se confirma con Mikel y Gabriel entre estas opciones, que pueden combinarse: el código `DATA_NOT_AVAILABLE` (ya definido en el contrato del gateway, S1-07) y/o un campo de calidad del dato en cada indicador (nombre por definir). Prueba: en un curso con una actividad **sin finalización de actividad configurada**, el progreso de esa actividad se devuelve como no disponible y no como 0 %, y el agente lo dice así. |
| RF-07 | El sistema no guarda ni expone el contenido de las entregas de los estudiantes. | El campo `onlinetext` no se persiste en la base de datos, no aparece en los logs de ningún servicio y no aparece en las respuestas de la API. Los datos sincronizados contienen solo identificador, estado, estado de calificación y fechas. Prueba: sincronizar una entrega que tenga `onlinetext` y comprobar que el texto no está en la base de datos, ni en los logs, ni en las respuestas del gateway ni de `moodle-sync`. |
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
| RF-19 | Las sincronizaciones quedan auditadas. | Cada sincronización registra internamente quién la lanzó, cuándo y con qué resultado, y esto se verifica en la base de datos. **Pendiente de definir** (pregunta 14): si la auditoría es solo interna o si el docente o el administrador podrán consultar un historial mediante un endpoint. Hoy el contrato (S1-07) solo expone el estado de la última sincronización; si se decide ofrecer un historial, el endpoint se agrega al contrato con una versión nueva. |

## 4. Requisitos no funcionales

| ID | Requisito | Criterio verificable |
|---|---|---|
| RNF-01 | Rendimiento. | Referencia: un docente, tres cursos y 50 estudiantes por curso. Primera respuesta del chat en 10 s o menos; respuesta completa en 60 s o menos; sincronización de un curso de 50 estudiantes en 2 minutos o menos; dashboard en 3 s o menos. Se mide en S1-12 y se repite en el Sprint 5. |
| RNF-02 | Privacidad de los datos. | El modelo corre en local (Ollama) y no se envían datos de estudiantes a servicios externos. No hay datos reales en el repositorio. El tipo de datos que se usará en el proyecto se define con la pregunta 11. |
| RNF-03 | Seguridad de secretos. | El repositorio solo contiene `.env.example`. El CI falla si hay un `.env` versionado. |
| RNF-04 | Seguridad de acceso. | La autorización por curso y la expiración del JWT tienen pruebas automáticas. Se refuerzan JWT, CORS y secretos en el Sprint 4. |
| RNF-05 | Resistencia del agente a instrucciones escondidas. | El agente ignora instrucciones dentro de los datos que lee (por ejemplo, el nombre de una actividad) en los escenarios de seguridad. |
| RNF-06 | Fiabilidad del agente. | Rechaza el 100 % de los accesos no autorizados, no inventa datos en ningún escenario de falla, y al menos el 90 % de las cifras que cita coincide con la fuente. |
| RNF-07 | Solo lectura sobre Moodle. | Ninguna llamada del sistema modifica datos en Moodle. Pruebas: (1) una prueba automática comprueba que el cliente de Moodle de `moodle-sync` solo puede invocar una lista cerrada de funciones de lectura y falla si se intenta llamar a cualquier función fuera de esa lista o con nombre de escritura (`create`, `update`, `delete`, `set`, `add`, `submit`); (2) el token del servicio web de Moodle se configura con esas funciones únicamente, lo que se comprueba intentando una función de escritura y obteniendo un rechazo. |
| RNF-08 | Calidad del código. | Cobertura mínima del 70 % en `analytics-service` y `agent-service`. Cada PR ejecuta pruebas y linters y no se une si fallan. |
| RNF-09 | Contratos de API. | Los contratos OpenAPI están versionados (v1, v2) y definitivos el D4 del Sprint 1. Quitar o renombrar campos exige una versión nueva. |
| RNF-10 | Ejecución reproducible. | Con `docker-compose` el proyecto se levanta en la máquina de cada integrante. |
| RNF-11 | Trazabilidad de los datos. | Cada dato mostrado puede rastrearse hasta su origen en Moodle y a la fecha de sincronización. |

## 5. Requisitos de interfaz

**Responsable:** Benjamín.
**Estado:** propuesta del Sprint 1, pendiente de revisión del equipo y del Product Owner.

Estos requisitos describen el comportamiento esperado de la interfaz. En el Sprint 1 se revisa su coherencia con el alcance, los contratos y los wireframes de S1-13; las comprobaciones funcionales se realizarán al implementar las pantallas en los sprints indicados en la matriz. Especificar un requisito no significa que su pantalla ya esté implementada o probada.

| ID | Pantalla | Requisitos de interfaz | Criterio verificable |
|---|---|---|---|
| RI-01 | Login | Mostrar campos obligatorios de correo y contraseña, con etiquetas visibles, contraseña oculta y botón «Iniciar sesión». Mostrar validaciones junto a los campos, un estado de espera durante el acceso y un mensaje comprensible cuando las credenciales sean inválidas. | Con campos vacíos o correo de formato inválido no se envía la solicitud y se identifica el campo que debe corregirse. Con respuesta exitosa se abre la lista de cursos; con `INVALID_CREDENTIALS` se permanece en el login y se informa el error. Mientras la solicitud está pendiente no se permite enviarla otra vez. |
| RI-02 | Lista de cursos | Mostrar los cursos autorizados devueltos por la API, con nombre completo, nombre corto y acción para abrir cada curso. Mostrar cantidad de estudiantes y fecha de sincronización cuando esos datos estén disponibles. | Cada curso mostrado corresponde a un elemento de la respuesta y su acción abre el curso con el mismo identificador. Una respuesta exitosa sin cursos muestra «No tienes cursos asignados». Si falta `studentCount` se muestra «No disponible»; si falta `lastSyncAt`, «Sin fecha disponible». Un valor de cero estudiantes se conserva como 0. |
| RI-03 | Dashboard de curso | Mostrar el curso seleccionado, promedio, tasas de entrega, calificación, finalización y pendientes de calificar, además de sus conteos. Incluir el listado paginado de estudiantes con acceso a su ficha, el estado de sincronización y la acción «Sincronizar». Mostrar la fecha del último éxito de sincronización y la fecha del cálculo como datos distintos. | Las tarjetas reproducen los indicadores entregados por analytics, con su unidad y calidad. Cambiar de página no recalcula las métricas del curso usando solo los estudiantes visibles. Al recibir 202 se muestra «Sincronizando»; mientras el estado sea `running`, o se reciba `SYNC_IN_PROGRESS`, se impiden solicitudes duplicadas. Solo al consultar `succeeded` se anuncia el éxito y se recargan los datos. Con `never` se muestra «Nunca sincronizado»; con `failed`, el error y la fecha del último éxito si existe. |
| RI-04 | Ficha individual del estudiante | Mostrar el nombre del estudiante, el curso, sus indicadores y las actividades con calificación y escala, estado de calificación, estado de entrega y progreso. Permitir regresar al curso. Los indicadores agregados provienen de analytics; las calificaciones y el progreso por actividad, del gateway. | El estudiante y el curso corresponden a los identificadores seleccionados. Una nota `graded` con `score = 0` aparece como 0 sobre la escala indicada. `pending_grading` con nota nula se muestra como «Pendiente de calificar»; `not_submitted` con entrega `none`, como «Sin entrega». Una entrega `draft` se identifica como «Borrador sin enviar»; si tiene una nota válida, también se conserva esa nota. `completionState = not_available` se muestra como «Finalización no disponible», sin convertirlo en 0 % ni en «Incompleta». |
| RI-05 | Alertas con sus evidencias | Mostrar las alertas del curso con la regla, severidad, estado activo o resuelto, fecha de detección y estudiante afectado, cuando corresponda. Permitir consultar la evidencia: métrica, valor observado, umbral, explicación y referencias disponibles. La severidad se identifica con texto además de color. | Cada alerta corresponde a la respuesta de la API. El detalle reproduce su regla, valores y explicación, sin fijar umbrales en la interfaz. Si `studentId` es nulo, se indica que la alerta corresponde al curso. Los valores ausentes se muestran como no disponibles. `NO_DATA` se presenta como falta de información, sin atribuir bajo rendimiento al estudiante. Una respuesta exitosa con lista vacía muestra «No hay alertas para esta consulta». |
| RI-06 | Chat con el agente | Mostrar el curso de referencia, los mensajes del docente y las respuestas del agente diferenciados, una caja de texto y el botón «Enviar». Mostrar «Procesando consulta» mientras se espera. Presentar las respuestas en bloques de «Hechos», «Inferencias» y «Recomendaciones», junto con sus fuentes, fecha de sincronización y avisos de datos no disponibles o resultados parciales. | Un mensaje vacío o compuesto solo por espacios no se envía. Durante una solicitud pendiente se impide el envío duplicado. La respuesta se presenta a partir de `answer.facts`, `answer.inferences`, `answer.recommendations` y `answer.unavailable`; un bloque sin contenido se identifica como tal. Con `meta.status = partial` se avisa que la respuesta es parcial. Un fallo o `TOOL_TIMEOUT` muestra un mensaje comprensible, conserva la consulta y permite reintentar cuando haya terminado la solicitud. La interfaz no completa respuestas con cifras inventadas. |
| RI-07 | Informe de curso | Mostrar el curso, período informado, métricas, hallazgos, fecha del cálculo y cantidad de alertas activas cuando esté disponible. La presentación final del informe queda sujeta a lo que resuelva el Product Owner en la pregunta 2. | Los datos corresponden al curso y al resultado del servicio. Se conserva la unidad y calidad de cada métrica. Un extremo del período ausente se identifica como «No especificado» y no se sustituye por la fecha actual. La fecha del cálculo se obtiene de `snapshot.calculatedAt`. La ausencia de `activeAlertCount` se muestra como «No disponible»; un valor 0 se muestra como 0. |
| RI-08 | Estados vacíos y de error | Mantener estados diferenciados de carga, contenido, ausencia de resultados, datos parciales y error. Mostrar acciones adecuadas para volver, iniciar sesión o reintentar, según corresponda. Mantener visibles el curso y el estudiante de referencia cuando la consulta sea válida. | Una respuesta exitosa vacía muestra el mensaje específico de la pantalla; un error de red o del servicio muestra un error, no una lista vacía. Una sesión vencida o inválida en una pantalla protegida lleva al login con un aviso. `COURSE_NOT_AUTHORIZED` muestra «No tienes acceso a este curso» sin mostrar sus datos. `MOODLE_UNAVAILABLE` informa que no se pudo actualizar; cualquier dato previo que se conserve mantiene su fecha y no se presenta como recién sincronizado. Al cambiar de curso se retira el contenido del curso anterior durante la nueva carga. |

### 5.1 Reglas comunes de presentación

- **Datos ausentes y calidad:** un valor nulo nunca se muestra como 0. Una métrica `unavailable` se presenta como «Dato no disponible», con su explicación si viene en la respuesta. Una métrica o un conjunto de datos `partial` lleva un aviso visible de «Datos parciales». Un 0 con estado `available` sí se muestra como 0.
- **Escalas y cálculos:** los indicadores se muestran con la unidad que devuelve analytics; los promedios normalizados del MVP se identifican como «sobre 10» y las tasas como porcentajes. La interfaz no calcula de nuevo promedios, tasas, umbrales o alertas. Las notas por actividad conservan la referencia `score`/`maxScore`; el caso de escalas distintas de 10 se confirma en la sección 5.2.
- **Fechas:** distinguir la última sincronización exitosa (`lastSuccessAt` en el estado de sincronización) de la fecha del cálculo (`snapshot.calculatedAt`). En el chat se muestra `meta.lastSyncAt` cuando exista. Una fecha ausente no se reemplaza por la hora actual ni se interpreta por sí sola como «Nunca sincronizado».
- **Progreso por actividad:** traducir `complete`, `incomplete`, `passed`, `failed` y `not_available` como «Completada», «Incompleta», «Completada y aprobada», «Completada sin aprobar» y «Finalización no disponible», respectivamente. Estas etiquetas describen la finalización de la actividad, no la aprobación del curso.
- **Navegación y lectura:** usar etiquetas visibles en formularios y acciones, e identificar los errores, estados y severidades con texto. Las pantallas de curso mantienen una acción para volver a la lista de cursos; las fichas permiten volver a su curso.
- **Mensajes independientes:** el diseño actual del agente propone consultas independientes en v1. El historial que se muestre en pantalla no debe presentarse como memoria del agente. La continuidad de conversación sigue pendiente de la pregunta 4 al Product Owner.

### 5.2 Dependencias y puntos por confirmar

| Con quién | Punto pendiente | Criterio provisional de interfaz |
|---|---|---|
| Mikel | Confirmar que el gateway expone las rutas de analytics definidas en `analytics.v1.yaml`; su OpenAPI actual las menciona, pero no las enumera. | La interfaz consulta los datos académicos por el gateway. Para el diseño se utilizan los esquemas publicados y se registra cualquier ajuste de contrato que haga falta. |
| Juan | Confirmar el cuerpo completo de `POST /chat`, cómo se comunica el curso de referencia y el formato de los errores. El diseño ya define la estructura de la respuesta. | Diseñar el chat con el curso visible, los tres bloques de respuesta, fuentes y avisos de datos no disponibles. Los nombres de campos de entrada pendientes no se dan por acordados. |
| Gabriel y Mikel | Confirmar cómo se mostrará una nota individual cuyo `maxScore` sea distinto de 10. El gateway entrega nota y escala originales, mientras las reglas proponen escala funcional 0 a 10 para el MVP. | Los ejemplos del MVP usan actividades sobre 10. Se conserva la escala original para no etiquetar, por ejemplo, 80 sobre 100 como 80 sobre 10. La normalización necesaria debe acordarse en los servicios antes de implementar este caso. |
| Gabriel y Product Owner | Confirmar los umbrales, el tratamiento de los borradores y cualquier excepción para un borrador ya calificado. Las preguntas 10 y 15 siguen abiertas. | Mostrar los estados de entrega y calificación recibidos de forma separada; los indicadores y las alertas se toman de analytics. La interfaz no decide qué cuenta como entrega. |
| Product Owner, Gabriel y Juan | Cerrar el contenido, período y formato del informe de la pregunta 2. El contrato actual entrega datos del informe, pero no define una descarga ni un filtro por rango de fechas. | Diseñar la consulta con los campos existentes y marcar los que falten. La exportación y la selección de períodos quedan pendientes de ese acuerdo. |

Referencias para la revisión: [contrato del gateway](../contracts/api-gateway.v1.yaml), [contrato de analytics](../contracts/analytics.v1.yaml), [reglas de indicadores](../analytics-rules/reglas-iniciales.md) y [diseño del agente](../agent-design/diseno-agente.md). Los seis wireframes de S1-13 cubrirán login, cursos, dashboard, ficha individual, alertas y chat; RI-07 define desde ahora la pantalla de informe prevista para el Sprint 5 y RI-08 se aplica de forma transversal.

## 6. Matriz de cumplimiento inicial

Se actualiza en la revisión de cada sprint.

| ID | Sprint | Responsable | Estado |
|---|---|---|---|
| RF-01 | S2 | Mikel | Pendiente |
| RF-02 | S2 | Mikel | Pendiente |
| RF-03 | S2 | Mikel | Pendiente |
| RF-04 | S2 | Mikel | Contrato en borrador (S1-07) |
| RF-05 | S2 | Mikel y Gabriel | Evidencia en S1-06; contrato en borrador (S1-07); tratamiento del borrador pendiente (pregunta 15) |
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
| RF-19 | S4 | Mikel | Alcance por definir (pregunta 14) |
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
| RI-01 | S2 | Benjamín | Especificado en S1; pendiente de revisión e implementación |
| RI-02 | S2 | Benjamín | Especificado en S1; pendiente de revisión e implementación |
| RI-03 | S3 | Benjamín | Especificado en S1; pendiente de revisión e implementación |
| RI-04 | S3 | Benjamín | Especificado en S1; pendiente de revisión e implementación |
| RI-05 | S4 | Benjamín | Especificado en S1; pendiente de revisión e implementación |
| RI-06 | S4 a S5 | Benjamín | Especificado en S1; pendiente de revisión e implementación |
| RI-07 | S5 | Benjamín | Especificado en S1; formato pendiente del Product Owner e implementación |
| RI-08 | S2 a S5 | Benjamín | Especificado en S1; estados generales previstos en S3, pendientes de revisión e implementación |

Los requisitos RI-01 a RI-08 se especifican en S1-03. La columna Sprint indica cuándo se implementan; RI-08 se aplica desde las primeras pantallas, con el trabajo general de estados vacíos y de error previsto para S3. Su incorporación a esta matriz no acredita implementación, pruebas ni aceptación del Product Owner.

## 7. Supuestos y restricciones

- Se usa Moodle 5.2.4 en Docker. Hasta ahora las pruebas usan datos ficticios; el tipo de datos del proyecto se confirma con la pregunta 11.
- Hay cinco servicios: `api-gateway`, `auth-courses`, `moodle-sync`, `analytics` y `agent-service`, con una sola instancia de SQL Server y un esquema por servicio.
- Las metas de rendimiento y de evaluación del agente son propuestas hasta que el Product Owner las apruebe.
- El modelo local se propone de forma provisional en S1-12 (`qwen3:1.7b`) y se confirma con los escenarios de evaluación.

## 8. Preguntas abiertas para el Product Owner

Las preguntas 1 a 10 son las del plan de proyecto (sección 11); la 11 en adelante surgieron al revisar los PRs y la evidencia de Moodle.

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
11. ¿Qué datos se usarán en el proyecto: datos ficticios, datos reales anonimizados o una instancia institucional autorizada? Si se usan datos reales, ¿qué autorización y qué anonimización se exigen, y quién las aprueba?

Preguntas surgidas durante la revisión de S1-06 y S1-07:

12. ¿Debe contemplarse el inicio de sesión institucional con Microsoft en una versión posterior? Si es así, ¿reemplazaría al inicio de sesión con correo y contraseña o convivirían?
13. ¿Qué puede ver y hacer el rol administrador? En concreto: si accede a todos los cursos o solo a los que se le asignen, y si puede ver los cursos y los estudiantes de otros docentes.
14. ¿La auditoría de las sincronizaciones es solo interna, o el docente o el administrador deben poder consultar un historial mediante un endpoint? (RF-19)
15. ¿Una entrega en borrador cuenta como "no entregada" en los indicadores y las alertas? (RF-05)
