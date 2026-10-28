# Reglas iniciales de analytics (S1-10)

**Responsable:** Gabriel
**Estado:** borrador para revisión
**Escala funcional del MVP:** 0 a 10
**Fuente:** contratos S1-07 y evidencia S1-06.

## 1. Convenciones de datos

| Estado | Significado | ¿Entra al promedio? | ¿Cuenta como entrega? |
|---|---|---:|---:|
| `graded` con `score = 0` | Nota cero válida. | Sí, como 0. | Sí. |
| `graded` con `score > 0` | Nota calificada. | Sí. | Sí. |
| `pending_grading` con `score = NULL` | Entregada, todavía sin calificar. | No. | Sí. |
| `not_submitted` con `score = NULL` | No hay entrega enviada. | No. | No. |
| `draft` / `submissionStatus = draft` | Borrador no enviado. | No. | No para el MVP. |
| Dato de finalización ausente | Moodle no configuró seguimiento. | No aplica. | No aplica. Es `DATA_NOT_AVAILABLE`. |

Un `score = NULL` nunca se transforma en cero. Una cifra calculada con denominador cero se devuelve como `NULL` con calidad `unavailable`, nunca como cero.

## 2. Normalización de calificaciones

Para cada calificación `g` con `status = graded`:

```text
score10(g) = round(10 * score / maxScore, 2)
```

Condiciones:

- `maxScore` debe ser mayor que cero.
- `score` debe estar entre 0 y `maxScore`; si no, el registro se marca inválido y no participa en el cálculo.
- En el MVP la interfaz muestra escala 0–10. La prueba de Moodle con escala 0–100 solo demuestra que debe conservarse `maxScore`; no amplía el alcance funcional.
- El redondeo se realiza al final de cada indicador, no antes de acumular valores.

## 3. Indicadores de curso

El período de cálculo es el conjunto de datos de la última sincronización exitosa del curso, salvo que el contrato reciba explícitamente otro rango.

### 3.1 Promedio de calificaciones

```text
averageScore10 = sum(score10(g) de grades graded) / count(grades graded)
```

Incluye las notas cero calificadas. Excluye `pending_grading`, `not_submitted`, borradores y registros inválidos.

**Ejemplo:** notas `8`, `0`, pendiente y sin entrega, todas sobre 10:

```text
averageScore10 = (8 + 0) / 2 = 4.00
```

### 3.2 Tasa de entrega

```text
submissionRate = 100 * submittedStudentsActivities / expectedStudentActivities
```

Donde:

- `expectedStudentActivities` = estudiantes matriculados × actividades evaluables consideradas.
- `submittedStudentsActivities` = registros con `status = graded` o `pending_grading`.
- Los borradores y ausencias no cuentan como entrega.

Si no hay estudiantes o actividades evaluables, el resultado es `NULL` y calidad `unavailable`.

### 3.3 Tasa de calificación

```text
gradingRate = 100 * graded / (graded + pending_grading)
```

No usa estudiantes sin entrega como pendientes de calificar. Si no hay entregas, devuelve `NULL`.

### 3.4 Tasa de finalización

Solo se calcula sobre actividades con seguimiento configurado en Moodle:

```text
completionRate = 100 * completedObserved / completionObservations
```

`state` 1, 2 o 3 cuenta como completado; `state` 0 cuenta como incompleto. Una actividad que no aparece en la respuesta de Moodle no entra al denominador y produce calidad `partial` si existen otras actividades o `unavailable` si no existe ninguna observación.

### 3.5 Pendientes de calificar

```text
pendingGradingRate = 100 * pending_grading / (graded + pending_grading + not_submitted)
```

Se muestra además el conteo absoluto. Un pendiente no se inventa como nota cero.

## 4. Indicadores por estudiante

Se aplican las mismas fórmulas, filtradas por `student_id` y curso. Para `submissionRate`, el denominador son las actividades evaluables del curso. Para `completionRate`, solo las actividades con observación válida para ese estudiante.

Indicadores mínimos de la ficha:

- `averageScore10`.
- `submissionRate`.
- `gradingRate`.
- `completionRate`.
- `gradedCount`, `pendingGradingCount`, `notSubmittedCount`.
- `dataQuality` y `calculatedAt`.

No se calcula “promedio” con un valor imputado para una ausencia. Si no hay notas calificadas, se devuelve `averageScore10 = NULL`.

## 5. Reglas iniciales de alertas

Las reglas son configurables en `analytics.alert_rule`; los valores siguientes son umbrales iniciales del Sprint 1, no decisiones definitivas del Product Owner.

| Código | Nombre | Ámbito | Condición inicial | Severidad | Evidencia mínima |
|---|---|---|---|---|---|
| `LOW_AVERAGE` | Promedio bajo | Estudiante | `averageScore10 < 6.0` | `warning` | promedio, cantidad de notas y actividades fuente |
| `LOW_SUBMISSION` | Baja entrega | Estudiante | `submissionRate < 80` | `warning` | entregas enviadas, esperadas y porcentaje |
| `PENDING_GRADING` | Entregas pendientes | Curso/estudiante | `pendingGradingRate > 20` | `info` | pendientes, entregas y porcentaje |
| `LOW_COMPLETION` | Baja finalización | Estudiante | `completionRate < 70` | `warning` | completadas, observadas y actividades con tracking |
| `NO_DATA` | Datos insuficientes | Curso/estudiante | métrica necesaria es `NULL` | `info` | código `DATA_NOT_AVAILABLE` y causa |

### 5.1 Reglas de evaluación

- Las comparaciones usan el valor sin redondear; la presentación redondea a dos decimales.
- `LOW_AVERAGE` requiere al menos 2 calificaciones `graded`, para evitar alertas por una sola observación. El mínimo debe ser configurable (`minGradedCount`, inicial 2).
- `LOW_SUBMISSION` requiere al menos 1 actividad evaluable y 1 estudiante esperado.
- `PENDING_GRADING` no se dispara si no hay entregas; en ese caso no hay evidencia de atraso.
- `LOW_COMPLETION` no se dispara cuando la finalización es `unavailable`; se genera `NO_DATA` en su lugar.
- Una alerta se identifica por regla, curso, estudiante opcional y `snapshot_id`; recalcular el mismo snapshot debe ser idempotente.
- Cada alerta debe incluir regla aplicada, valor observado, umbral, período/snapshot, fecha de cálculo y referencias a la evidencia.

## 6. Calidad del dato

`dataQuality` puede ser:

- `complete`: todos los insumos requeridos están disponibles.
- `partial`: algunos insumos están disponibles, pero faltan otros; no se imputan valores.
- `unavailable`: no existe insumo suficiente para calcular la métrica.

Código de respuesta para una métrica ausente:

```json
{
  "value": null,
  "status": "unavailable",
  "code": "DATA_NOT_AVAILABLE",
  "detail": "Moodle no configuró el seguimiento de finalización para las actividades observadas."
}
```

## 7. Ejemplo completo

Datos de un estudiante en cuatro actividades:

| Actividad | Estado | Score | Máximo |
|---|---|---:|---:|
| Tarea 1 | `graded` | 8 | 10 |
| Tarea 2 | `graded` | 0 | 10 |
| Tarea 3 | `pending_grading` | NULL | 10 |
| Tarea 4 | `not_submitted` | NULL | 10 |

Resultados:

```text
averageScore10 = (8 + 0) / 2 = 4.00
submissionRate = 2 / 4 * 100 = 50.00
pendingGradingRate = 1 / 4 * 100 = 25.00
```

Se activarían `LOW_AVERAGE` y `LOW_SUBMISSION`. También `PENDING_GRADING` porque supera 20 %. No se activa `LOW_COMPLETION` si Moodle no entregó observaciones de finalización; se devuelve `NO_DATA`.

## 8. Configuración y versionado

- Los umbrales se almacenan en la base de datos y se pueden cambiar sin modificar código.
- Cada cambio de regla debe registrar quién lo hizo, cuándo y el valor anterior/nuevo en la implementación de Sprint 2 o posterior.
- Cambiar el significado de un indicador requiere revisar este documento y versionar el contrato si cambia la respuesta pública.
- Los umbrales se validan: porcentajes entre 0 y 100; notas entre 0 y 10; `minGradedCount` entero mayor o igual que 1.
