# Modelo entidad-relación de EduMonitor AI (S1-10)

**Responsable:** Gabriel
**Estado:** borrador para revisión
**Fecha:** 2026-10-22
**Fuente:** contratos OpenAPI S1-07, evidencia S1-06 y reglas de analytics S1-09.

## 1. Decisiones del modelo

- La base usa una sola instancia de SQL Server 2022, con un esquema por servicio: `auth`, `sync`, `analytics` y `agent`.
- Los servicios no comparten tablas. Las relaciones entre esquemas se representan mediante identificadores (`course_id`, `student_id`, `activity_id`, `sync_id`, `alert_id`), no mediante claves foráneas entre servicios.
- `student_id` es el `id` estable de Moodle. No se usa `username` como clave.
- El origen de calificaciones es `sync`; analytics guarda resultados calculados y su evidencia, no una segunda copia de las calificaciones.
- La escala funcional del MVP es de 0 a 10. Si una fuente entrega otra escala, se conserva `max_score` y se normaliza a 0–10 antes de calcular indicadores; nunca se comparan puntajes crudos de escalas distintas.
- `score = 0` con `status = graded` es una nota cero válida. `score = NULL` con `pending_grading` o `not_submitted` no se convierte en cero.
- Un borrador de entrega se conserva como metadato técnico (`submission_status = draft`) y se trata como no entregado para los indicadores del MVP.
- El contenido `onlinetext` no pertenece al modelo: se descarta durante la sincronización y tampoco se guarda en logs de analytics.
- La finalización no configurada en Moodle se representa como dato no disponible, nunca como `0 %`.

## 2. Diagrama lógico

```mermaid
erDiagram
    AUTH_USER ||--o{ AUTH_COURSE_ACCESS : autoriza
    AUTH_COURSE_ACCESS }o--|| SYNC_COURSE : "course_id"

    SYNC_COURSE ||--o{ SYNC_STUDENT_ENROLLMENT : matricula
    SYNC_STUDENT_ENROLLMENT }o--|| SYNC_STUDENT : "student_id"
    SYNC_COURSE ||--o{ SYNC_ACTIVITY : contiene
    SYNC_ACTIVITY ||--o{ SYNC_GRADE : recibe
    SYNC_STUDENT ||--o{ SYNC_GRADE : obtiene
    SYNC_COURSE ||--o{ SYNC_SYNC_RUN : sincroniza
    SYNC_STUDENT ||--o{ SYNC_COMPLETION : registra
    SYNC_ACTIVITY ||--o{ SYNC_COMPLETION : "activity_id"

    SYNC_COURSE ||--o{ ANALYTICS_COURSE_SNAPSHOT : resume
    SYNC_STUDENT ||--o{ ANALYTICS_STUDENT_SNAPSHOT : resume
    ANALYTICS_COURSE_SNAPSHOT ||--o{ ANALYTICS_STUDENT_SNAPSHOT : contiene
    ANALYTICS_COURSE_SNAPSHOT ||--o{ ANALYTICS_ALERT : genera
    ANALYTICS_ALERT_RULE ||--o{ ANALYTICS_ALERT : dispara
    ANALYTICS_ALERT ||--|{ ANALYTICS_ALERT_EVIDENCE : explica
    SYNC_GRADE ||--o{ ANALYTICS_ALERT_EVIDENCE : sustenta
    SYNC_COMPLETION ||--o{ ANALYTICS_ALERT_EVIDENCE : sustenta
    SYNC_SYNC_RUN ||--o{ ANALYTICS_COURSE_SNAPSHOT : origina

    AGENT_TRACE }o--|| AUTH_USER : "teacher_id"
    AGENT_TRACE }o--|| SYNC_COURSE : "course_id opcional"
    AGENT_TRACE }o--o{ ANALYTICS_ALERT : "alert_id en resumen"

    AUTH_USER {
        int user_id PK
        string email
        string name
        string role
    }
    AUTH_COURSE_ACCESS {
        int user_id PK
        int course_id PK
        datetime granted_at
    }
    SYNC_COURSE {
        int course_id PK
        string short_name
        string full_name
        datetime last_sync_at
    }
    SYNC_STUDENT {
        int student_id PK
        string full_name
        string email
    }
    SYNC_STUDENT_ENROLLMENT {
        int course_id PK
        int student_id PK
        string role
        datetime enrolled_at
    }
    SYNC_ACTIVITY {
        int activity_id PK
        int course_id
        string name
        decimal max_score
        string completion_tracking
    }
    SYNC_GRADE {
        int grade_id PK
        int course_id
        int student_id
        int activity_id
        string status
        string submission_status
        decimal score_nullable
        decimal max_score
        datetime submitted_at_nullable
        datetime graded_at_nullable
        datetime synced_at
    }
    SYNC_COMPLETION {
        int completion_id PK
        int course_id
        int student_id
        int activity_id
        int state
        string availability
        datetime observed_at
    }
    SYNC_SYNC_RUN {
        string sync_id PK
        int course_id
        string state
        datetime started_at
        datetime finished_at_nullable
        string error_code_nullable
    }
    ANALYTICS_COURSE_SNAPSHOT {
        string snapshot_id PK
        int course_id
        string sync_id
        datetime calculated_at
        decimal average_score_nullable
        decimal submission_rate_nullable
        decimal completion_rate_nullable
        int graded_count
        int pending_count
        int not_submitted_count
        string data_quality
    }
    ANALYTICS_STUDENT_SNAPSHOT {
        string snapshot_id PK
        int course_snapshot_id
        int student_id
        decimal average_score_nullable
        decimal submission_rate_nullable
        decimal completion_rate_nullable
        int alert_count
        string data_quality
    }
    ANALYTICS_ALERT_RULE {
        string rule_code PK
        string name
        string metric
        string operator
        decimal threshold
        boolean enabled
        datetime updated_at
    }
    ANALYTICS_ALERT {
        string alert_id PK
        string snapshot_id
        string rule_code
        int student_id_nullable
        string severity
        string status
        datetime detected_at
        datetime resolved_at_nullable
    }
    ANALYTICS_ALERT_EVIDENCE {
        string evidence_id PK
        string alert_id
        string source_type
        string source_id
        string metric
        decimal observed_value_nullable
        decimal threshold_nullable
        string explanation
    }
    AGENT_TRACE {
        string trace_id PK
        int teacher_id
        int course_id_nullable
        datetime started_at
        datetime finished_at
        string status
    }
```

## 3. Entidades y responsabilidades

| Esquema | Entidad | Responsabilidad | Regla de retención/dato |
|---|---|---|---|
| `auth` | `user` | Usuario y rol del sistema. | No contiene credenciales en analytics. |
| `auth` | `course_access` | Autorización docente-curso. | El gateway valida el acceso antes de llamar a analytics. |
| `sync` | `course`, `student`, `student_enrollment` | Catálogo y matrícula normalizados desde Moodle. | `student_id` es el id de Moodle. |
| `sync` | `activity`, `grade` | Actividades y calificaciones normalizadas. | `grade` no guarda `onlinetext`; conserva estados y fechas. |
| `sync` | `completion` | Estado de finalización observado en Moodle. | Ausencia de fila puede significar `DATA_NOT_AVAILABLE`, no incompleto. |
| `sync` | `sync_run` | Auditoría técnica de sincronización. | Incluye quién/curso/estado/fechas en la implementación final. |
| `analytics` | `course_snapshot`, `student_snapshot` | Resultados calculados reproducibles por sincronización. | Se pueden recalcular desde `sync` y se guarda la fecha/origen. |
| `analytics` | `alert_rule` | Umbrales configurables sin cambiar código. | Toda regla tiene código estable y versión implícita por `updated_at`. |
| `analytics` | `alert`, `alert_evidence` | Alertas explicables y su evidencia. | Una alerta no existe sin al menos una evidencia. |
| `agent` | `trace` | Trazabilidad del agente. | No guarda JWT, `onlinetext` ni salida completa de Moodle. |

## 4. Integridad y casos especiales

1. Una fila de `sync.grade` es única por `(course_id, student_id, activity_id, sync_id)` o por la clave natural equivalente definida por la migración. La sincronización posterior no debe duplicar la observación vigente.
2. Para calcular promedios solo entran calificaciones `graded` con `score` no nulo y `max_score > 0`.
3. `pending_grading`, `not_submitted` y `draft` se cuentan por separado para explicar el indicador; no se incluyen como ceros en el promedio.
4. Si no existe ninguna calificación `graded`, `average_score` es `NULL` y la calidad es `unavailable`, no `0`.
5. Si ninguna actividad tiene finalización configurada, `completion_rate` es `NULL` y la calidad es `unavailable`.
6. Los resultados de analytics deben identificar el `snapshot_id`, `calculated_at` y `sync_id` para poder rastrear cada cifra hasta la sincronización que la originó.
7. Los nombres y correos de estudiantes solo se devuelven según el contrato y autorización; las alertas y trazas deben preferir `student_id`.

## 5. Próximo paso de implementación

En Sprint 2, las migraciones deben crear primero los esquemas y tablas de `sync`, después `analytics` y finalmente los índices y restricciones. Las pruebas mínimas deben cubrir nota cero, `NULL`, pendiente, borrador, sin entrega, datos no disponibles y recomputación idempotente.
