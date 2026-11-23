# Demo masiva: 5 docentes, 25 cursos y 25 estudiantes por curso

Este conjunto de datos es completamente ficticio y está pensado para la demostración. Crea cinco docentes, cinco cursos por docente y 25 estudiantes por curso. En total son 25 cursos y 625 estudiantes.

El modo masivo es opcional. Si no se activa, el proyecto conserva la demo mínima actual con `docente1`, `docente2`, `PRUEBA01` y `PRUEBA02`.

## Qué archivos se agregaron

- `database/seed/002-demo-masivo.sql`: crea en Analytics 25 cursos, 625 estudiantes, calificaciones y progreso ficticios.
- `services/auth-courses-service/src/AuthCourses.Api/AuthDb.cs`: agrega el dataset masivo de Auth cuando se solicita.
- `infra/moodle/cursos-demo-masivo.csv.example`: plantilla para crear los 25 cursos en Moodle.
- `infra/moodle/usuarios-demo-masivo.csv.example`: plantilla con los cinco docentes y 625 estudiantes.

## Instalación desde cero para la demo masiva

Estos pasos borran los volúmenes locales de Docker. Solo deben usarse si no necesitan conservar la base actual.

En PowerShell, desde la raíz del repositorio:

```powershell
Copy-Item .env.example .env
notepad .env
```

En `.env`, cambien las contraseñas y dejen estas dos variables así:

```dotenv
AUTH_SEED_DATASET=massive
DEMO_DATASET=massive
```

No suban `.env` a GitHub. La contraseña de todos los docentes de Auth será la definida en `AUTH_SEED_PASSWORD`.

Después ejecuten:

```powershell
docker compose down -v
docker compose up -d --build
docker compose ps
```

El `down -v` es importante en una instalación desde cero porque el seed solo se aplica sobre bases nuevas. Si ya existen usuarios en Auth, el servicio no reemplaza ni duplica el dataset.

## Resultado esperado en Auth

Se crean estas cuentas:

```text
docente1@edumonitor.test
docente2@edumonitor.test
docente3@edumonitor.test
docente4@edumonitor.test
docente5@edumonitor.test
```

Todas usan la contraseña definida en `AUTH_SEED_PASSWORD`.

Cada docente recibe cinco cursos. Los cursos tienen estos nombres cortos:

```text
DEMO-01-01 a DEMO-01-05
DEMO-02-01 a DEMO-02-05
...
DEMO-05-01 a DEMO-05-05
```

Los IDs de Auth y Analytics son `201` a `225`. Cada curso tiene 25 estudiantes ficticios.

## Comprobación rápida

Inicien sesión con uno de los docentes y consulten sus cursos. Por ejemplo:

```powershell
$login = Invoke-RestMethod -Method Post `
  -Uri http://localhost:5001/auth/login `
  -ContentType 'application/json' `
  -Body (@{ email = 'docente1@edumonitor.test'; password = 'LA_CLAVE_DE_AUTH_SEED_PASSWORD' } | ConvertTo-Json)

$headers = @{ Authorization = "Bearer $($login.accessToken)" }
Invoke-RestMethod -Uri http://localhost:5001/courses -Headers $headers
```

La respuesta debe mostrar cinco cursos para `docente1`. Para comprobar un curso concreto:

```powershell
Invoke-RestMethod -Uri http://localhost:5003/api/v1/courses/201/analytics
```

El endpoint de Analytics debe devolver indicadores basados en 25 estudiantes.

También pueden ejecutar:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1 -RequireGateway
```

## Cargar los mismos datos en Moodle, de forma opcional

El seed de Auth y Analytics no crea cursos dentro de Moodle. Moodle asigna sus propios IDs y por eso los cursos creados allí pueden no tener los IDs `201` a `225`. Para cargar la parte ficticia en Moodle:

1. Levanten Moodle y entren como administrador.
2. Creen o seleccionen una categoría con ID `1`.
3. Vayan a `Site administration > Courses > Upload courses`.
4. Suban `infra/moodle/cursos-demo-masivo.csv.example`.
5. Seleccionen la opción para crear cursos nuevos y confirmen la categoría.
6. Verifiquen que aparezcan los 25 cursos `DEMO-01-01` a `DEMO-05-05`.
7. Copien `infra/moodle/usuarios-demo-masivo.csv.example` como `usuarios-demo-masivo.csv`.
8. Reemplacen `CAMBIAR-CLAVE` por una contraseña fuerte ficticia.
9. En `Site administration > Users > Accounts > Upload users`, suban el CSV.
10. Seleccionen `Add new only, skip existing users`, contraseña obligatoria desde el archivo y sin cambio obligatorio de contraseña.
11. Comprueben que cada curso tenga un docente y 25 estudiantes.
12. Comprueben también que exista el usuario `edumonitor_sync`, inscrito en los 25 cursos con el rol `teacher`.

El CSV de usuarios es una plantilla y no contiene contraseñas reales. No suban la copia modificada con contraseñas al repositorio.

## Crear actividades, entregas, notas y progreso en Moodle

Los CSV de Moodle no pueden crear actividades académicas ni calificaciones. Para que la demostración completa tenga datos reales dentro de Moodle, el compose monta el script `infra/moodle/seed-demo-academico.php` dentro del contenedor.

Después de cargar los cursos y usuarios, ejecuten desde la raíz del repositorio:

```powershell
docker compose exec -T moodle php /opt/bitnami/moodle/local/edumonitor_seed_massive.php
```

El script es idempotente para esta demo. Busca los cursos `DEMO-*`, crea dos actividades por curso y genera entregas, calificaciones y estados de finalización ficticios para los estudiantes inscritos. No contiene contraseñas, tokens ni datos reales.

El resultado esperado son dos actividades por curso, con casos de nota cero, nota pendiente, borrador, entrega y finalización incompleta o completa. Si el comando indica que no encontró cursos `DEMO-*`, primero deben cargar el CSV de cursos y usuarios.

## Usuario técnico para la sincronización

No usen el token de `docente1` en `MOODLE_WS_TOKEN`. El sincronizador utiliza un único token por ejecución y necesita leer los 25 cursos. El CSV crea el usuario técnico ficticio `edumonitor_sync` y lo inscribe en los 25 cursos.

En Moodle creen un token para `edumonitor_sync` dentro del servicio web `EduMonitor`. El servicio debe tener únicamente las funciones de lectura documentadas en `infra/moodle/README.md`. Después guarden el token solo en `.env`:

```dotenv
MOODLE_WS_TOKEN=TOKEN_DEL_USUARIO_EDUMONITOR_SYNC
```

El usuario técnico se usa únicamente para leer Moodle durante la sincronización. Los docentes siguen siendo los usuarios que inician sesión en EduMonitor y conservan sus cinco cursos autorizados en Auth.

## Sincronizar Moodle con el programa final

Después de cargar los cursos y usuarios, no es necesario editar los IDs de Moodle en SQL. Moodle puede asignar, por ejemplo, el ID `7` al curso `DEMO-01-01`, mientras Auth usa el ID canónico `201`.

`moodle-sync` resuelve automáticamente estos casos por el nombre corto:

```text
Auth/EduMonitor: 201 → DEMO-01-01
Moodle:          7   → DEMO-01-01
```

Desde la aplicación o desde el Gateway, el docente debe sincronizar usando el ID que muestra EduMonitor, por ejemplo:

```powershell
$login = Invoke-RestMethod -Method Post `
  -Uri http://localhost:5000/api/v1/auth/login `
  -ContentType 'application/json' `
  -Body (@{ email = 'docente1@edumonitor.test'; password = $env:AUTH_SEED_PASSWORD } | ConvertTo-Json)

$headers = @{ Authorization = "Bearer $($login.accessToken)" }
Invoke-RestMethod -Method Post `
  -Uri http://localhost:5000/api/v1/courses/201/sync `
  -Headers $headers
```

La respuesta inicial debe ser `202 Accepted`. Luego consulten el estado hasta que sea `succeeded`:

```powershell
Invoke-RestMethod -Method Get `
  -Uri http://localhost:5000/api/v1/courses/201/sync `
  -Headers $headers
```

El mismo procedimiento se repite con los cursos `202` a `225`. Cada docente solo puede sincronizar sus cinco cursos autorizados. Después de una sincronización exitosa, Analytics lee los datos guardados en el esquema `sync`, que ahora provienen de Moodle.

El programa conserva el ID canónico de EduMonitor en sus respuestas, pero usa internamente el ID real de Moodle para consultar estudiantes, actividades, notas y progreso. Por eso no deben cambiar manualmente los IDs ni borrar el seed SQL.

## Volver a la demo mínima

Para regresar a la demo original:

```dotenv
AUTH_SEED_DATASET=minimal
DEMO_DATASET=minimal
```

Luego, si se quiere borrar el dataset masivo de los volúmenes locales:

```powershell
docker compose down -v
docker compose up -d --build
```
