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
8. Reemplacen `CAMBIAR-CLAVE` por una contraseña fuerte.
9. En `Site administration > Users > Accounts > Upload users`, suban el CSV.
10. Seleccionen `Add new only, skip existing users`, contraseña obligatoria desde el archivo y sin cambio obligatorio de contraseña.
11. Comprueben que cada curso tenga un docente y 25 estudiantes.

El CSV de usuarios es una plantilla y no contiene contraseñas reales. No suban la copia modificada con contraseñas al repositorio.

## Si quieren sincronizar Moodle

Moodle puede asignar IDs diferentes a `201` a `225`. Antes de sincronizar un curso:

1. Obtengan el ID real desde la URL de Moodle.
2. Registren ese mismo ID y nombre corto en Auth Courses.
3. Usen el ID real en `POST /courses/{id}/sync`.
4. Comprueben el resultado con `GET /courses/{id}/sync`.

Para la demostración de Analytics no es obligatorio sincronizar los 25 cursos de Moodle: el dataset masivo de SQL ya deja disponibles los 25 cursos y sus 25 estudiantes por curso. Moodle se carga aparte cuando se quiera demostrar el flujo de sincronización real.

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
