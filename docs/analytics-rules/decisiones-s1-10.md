# Decisiones de S1-10: analytics

**Responsable:** Gabriel Rojas  
**Contrato:** `docs/contracts/analytics.v1.yaml`  
**Versión:** `1.0.0`  
**Estado:** decisiones técnicas del equipo; las decisiones de producto siguen sujetas a aceptación del Product Owner.

Este documento registra cómo se resolvieron las observaciones O-12 a O-20 de la revisión cruzada de contratos.

## O-12: relación entre borradores y no entregas

`notSubmittedCount` incluye todas las actividades sin una entrega enviada. `draftCount` es un subconjunto de `notSubmittedCount` y no se suma nuevamente. Un borrador conserva su identidad (`submissionStatus: draft`) para la interfaz y la trazabilidad, pero cuenta como no entregado para los indicadores del MVP.

Ejemplo: con 2 actividades calificadas, 1 pendiente de calificar, 1 borrador y 1 actividad sin entrega:

```text
gradedCount = 2
pendingGradingCount = 1
notSubmittedCount = 2
draftCount = 1
submissionRate = (2 + 1) / (2 + 1 + 2) * 100 = 60
```

El borrador está incluido en `notSubmittedCount`; `draftCount` sirve para explicar el desglose y no altera el denominador.

## O-13: estado de las alertas

`GET /api/v1/courses/{courseId}/analytics/alerts` admite el parámetro `status` con los valores `active` y `resolved`. Su valor predeterminado es `active`, porque la interfaz y el agente consultan primero alertas vigentes.

## O-14: autorización

Analytics recibe el JWT reenviado por el api-gateway. El gateway valida firma, expiración y autorización del docente para el curso; analytics vuelve a rechazar tokens ausentes o inválidos. Los servicios internos no deben publicar sus puertos fuera de la red interna de Docker. El contrato conserva respuestas `401` y `403`.

## O-15: trazabilidad de hallazgos

`CourseReportData.findings` deja de ser una lista de textos simples. Cada hallazgo puede incluir `alertId`, `ruleCode`, `studentId`, `metric` y siempre incluye `text`. De esta forma el agente puede citar la alerta o la métrica que originó el hallazgo.

## O-16: nombres de métricas

El contrato usa los mismos nombres que las reglas:

- `averageScore10` para el promedio normalizado.
- `gradedCount`, `pendingGradingCount`, `notSubmittedCount` y `draftCount` dentro de `counts`.
- `AlertEvidence.metric` solo admite `averageScore10`, `submissionRate`, `gradingRate`, `completionRate` y `pendingGradingRate`.

## O-17: validación de parámetros

Las rutas declaran `400 Bad Request` para parámetros inválidos, incluidos `page`, `pageSize`, `severity`, `status` y `snapshotId`. El cuerpo usa el esquema `Problem` con código `VALIDATION_ERROR`.

## O-18: snapshots en el MVP

El parámetro opcional `snapshotId` permite consultar una sincronización específica cuando el consumidor ya conoce su identificador. Si se omite, se consulta la última sincronización exitosa. El MVP no agrega una ruta para listar snapshots; esa capacidad queda fuera del contrato v1.

## O-19: reglas configurables

Cambiar umbrales no cambia el contrato. Agregar un nuevo `ruleCode` es compatible dentro de v1 si los consumidores tratan valores desconocidos como datos no reconocidos y no dependen de una lista rígida para funcionar. Quitar o renombrar un campo o una regla existente exige una nueva versión del contrato y aprobación de los consumidores.

## O-20: versión y puerto

El contrato queda declarado como `1.0.0`. Analytics usa el puerto local `5003`, coherente con `moodle-sync` en `5002`, el gateway en `5000` y auth-courses en `5001`. `.env.example` se actualiza para usar `ANALYTICS_URL=http://localhost:5003`.

## Pendientes del Product Owner

La decisión técnica de esta PR no sustituye la aceptación de producto. Siguen pendientes las preguntas sobre umbrales definitivos, tratamiento de datos reales, formato del informe, trazas y demás preguntas abiertas de `docs/requirements/requisitos.md`.
