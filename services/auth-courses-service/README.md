# auth-courses-service

**Responsable:** Mikel

Inicia sesión, emite el JWT y dice a qué cursos tiene acceso cada usuario. Contrato: `docs/contracts/auth-courses.v1.yaml` (puerto 5001). Es un servicio interno: el público entra por el api-gateway.

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `JWT_SECRET` | Sí | Secreto HS256, mínimo 32 caracteres |
| `JWT_ISSUER` | No | Por defecto `edumonitor` |
| `JWT_AUDIENCE` | No | Por defecto `edumonitor-api` |
| `JWT_EXPIRES_MINUTES` | No | Por defecto 60 |
| `AUTH_SEED_PASSWORD` | Para datos de prueba | Contraseña de los usuarios ficticios (docente1, docente2 y admin, `@edumonitor.test`) |
| `ConnectionStrings__Auth` | No | Cadena de SQL Server. Sin ella usa una base en memoria |

Ningún valor real va al repositorio: solo `.env.example`.

## Ejecutar y probar

```bash
export JWT_SECRET="una-clave-larga-de-al-menos-32-caracteres"
export AUTH_SEED_PASSWORD="elige-una-clave-de-prueba"
dotnet run --project src/AuthCourses.Api
dotnet test tests/AuthCourses.Tests
```

## Datos de prueba

| Usuario | Rol | Cursos |
|---|---|---|
| `docente1@edumonitor.test` | teacher | 2 (PRUEBA01) |
| `docente2@edumonitor.test` | teacher | 3 (PRUEBA02) |
| `admin@edumonitor.test` | admin | ninguno (pendiente de la pregunta 13 al Product Owner) |

Con SQL Server, las tablas se crean con `db/auth-001-esquema.sql` (esquema `auth`). Se moverá a `database/migrations` cuando Gabriel confirme su convención.
