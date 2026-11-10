# moodle-sync-service

**Responsable:** Mikel

Lee Moodle (solo lectura), traduce los datos al formato de EduMonitor y los entrega paginados. Contrato: `docs/contracts/moodle-sync.v1.yaml` (puerto 5002). Es un servicio interno: el público entra por el api-gateway, que ya comprobó el acceso al curso. Aun así valida el JWT que recibe.

## Rutas

| Ruta | Qué hace |
|---|---|
| `POST /courses/{courseId}/sync` | Inicia la sincronización (202). 409 `SYNC_IN_PROGRESS` si ya hay una; 503 `MOODLE_UNAVAILABLE` si Moodle no responde |
| `GET /courses/{courseId}/sync` | Estado y fecha: `never`, `running`, `succeeded` o `failed` |
| `GET /courses/{courseId}/students` | Estudiantes (paginado) |
| `GET /courses/{courseId}/students/{studentId}` | Ficha: notas y progreso de actividades |
| `GET /courses/{courseId}/grades` | Notas con su estado (paginado, filtros `studentId` y `activityId`) |

Si el curso nunca se sincronizó, las lecturas responden 503 `DATA_NOT_AVAILABLE`.

## Reglas de traducción

- **Nota:** con nota (incluido 0) = `graded`; entregó y sin nota = `pending_grading`; borrador o sin entrega = `not_submitted`. Una nota nula nunca es 0.
- **Entrega:** `submissionStatus` = `none`, `draft` o `submitted`.
- **Progreso:** `complete`, `incomplete`, `passed`, `failed` o `not_available` (sin seguimiento configurado o sin dato; nunca 0 ni nulo).
- **Estudiantes:** se identifican por su id de Moodle.
- **Privacidad:** nunca se lee ni se guarda el texto de las entregas (`onlinetext`). La salida tiene una lista de campos permitidos comprobada por pruebas.
- **Moodle:** solo funciones de lectura. El token va en el cuerpo del POST, nunca en la URL, y no se escribe en los registros. Un error de Moodle deja la sincronización en `failed` y no guarda datos a medias.

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `JWT_SECRET` | Sí | El mismo secreto que auth-courses (mínimo 32 caracteres) |
| `JWT_ISSUER` / `JWT_AUDIENCE` | No | Por defecto `edumonitor` y `edumonitor-api` |
| `MOODLE_BASE_URL` | No | Por defecto `http://localhost:8080` |
| `MOODLE_WS_TOKEN` | Sí, para sincronizar | Token del servicio web (nunca al repositorio) |

## Estado del almacenamiento

En ejecución normal utiliza `SqlSyncStore`, que persiste los datos en SQL Server usando el esquema `sync` existente:

- `sync.course`: cursos sincronizados.
- `sync.student`: estudiantes.
- `sync.grade`: calificaciones.
- `sync.completion`: progreso de actividades.

La conexión se obtiene de `ConnectionStrings__EduMonitor`, por ejemplo:

```text
Server=sqlserver,1433;Database=EduMonitor;User Id=sa;Password=...;TrustServerCertificate=True;
```

El adaptador `InMemorySyncStore` se utiliza únicamente en las pruebas automatizadas para mantenerlas aisladas y rápidas. Los datos guardados en SQL Server permanecen disponibles después de reiniciar el servicio y pueden ser consumidos por Analytics.

El texto de las entregas (`onlinetext`) nunca se lee, nunca se guarda y nunca se devuelve en las respuestas.

## Ejecutar y probar

```bash
export JWT_SECRET="una-clave-larga-de-al-menos-32-caracteres"
export MOODLE_WS_TOKEN="$(cat /c/edumonitor-moodle/token.txt)"
dotnet run --project src/MoodleSync.Api
dotnet test tests/MoodleSync.Tests
```
