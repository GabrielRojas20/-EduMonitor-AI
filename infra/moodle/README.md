# Moodle local para EduMonitor AI — Sprint 3

**Responsable:** Mikel

Esta instancia de Moodle se ejecuta en Docker y se utiliza únicamente para desarrollo y demostración con datos ficticios o anonimizados. La imagen definida por `docker-compose.yml` es `bitnamilegacy/moodle:4.5`; la instalación validada reportó Moodle **4.5.4**.

| Dato | Valor |
|---|---|
| Moodle | `bitnamilegacy/moodle:4.5` / instalación verificada `4.5.4` |
| Base de datos | MariaDB 11.4 |
| URL | `http://localhost:8080` |
| Administrador local | `admin` / valor de `MOODLE_ADMIN_PASSWORD` en `.env` |
| Usuario técnico de Web Service | `edumonitor_sync` |
| Servicio externo | `EduMonitor` |

## 1. Configuración segura

Desde la raíz del repositorio, copia el archivo de entorno y completa valores locales:

```bash
cp .env.example .env
```

Configura como mínimo `MOODLE_DB_PASSWORD`, `MOODLE_DB_ROOT_PASSWORD`, `MOODLE_ADMIN_PASSWORD`, `MOODLE_ADMIN_EMAIL`, `JWT_SECRET`, `AUTH_SEED_PASSWORD` y `MOODLE_WS_TOKEN`. El archivo `.env` está ignorado por Git y **no debe subirse**.

No pongas en GitHub la contraseña del administrador, el token de Moodle, `JWT_SECRET`, JWT de docentes ni contraseñas de usuarios. Para entregar el proyecto al ingeniero, comparte las credenciales demo por un canal privado o genera valores nuevos en su `.env`.

## 2. Levantar Moodle y el resto del entorno

Desde la raíz del repositorio:

```bash
docker compose up -d --build
docker compose ps
```

Puertos principales:

- Moodle: `8080`
- API Gateway: `5000`
- Auth Courses: `5001`
- Moodle Sync: `5002`
- Analytics: `5003`
- Agent Service local: `5004`
- Ollama: `11434`
- Frontend Vite: `5173`

El Agent Service se ejecuta fuera de Docker en el Compose actual. Para iniciarlo, consulta `services/agent-service/README.md` y utiliza `5004`.

## 3. Configurar el Web Service REST

En Moodle, como administrador:

1. Activa **Site administration → Advanced features → Enable web services**.
2. En **Server → Web services → Manage protocols**, habilita **REST**.
3. Crea un rol mínimo, por ejemplo `edumonitor_ws`, con la capacidad `webservice/rest:use` en contexto de sistema.
4. Crea o utiliza el usuario técnico `edumonitor_sync` y asígnale el rol.
5. En **External services**, crea o habilita el servicio `EduMonitor` y marca **Authorised users only**.
6. Añade las funciones de solo lectura: `core_webservice_get_site_info`, `core_enrol_get_users_courses`, `core_enrol_get_enrolled_users`, `gradereport_user_get_grade_items`, `core_course_get_contents`, `core_completion_get_activities_completion_status`, `mod_assign_get_assignments` y `mod_assign_get_submissions`.
7. Autoriza a `edumonitor_sync` en el servicio y genera un token. Guarda el token únicamente en `MOODLE_WS_TOKEN` del `.env`.

Comprobación sin mostrar el token:

```bash
docker compose exec -T moodle-sync sh -c '\
curl -sS -X POST "$MOODLE_BASE_URL/webservice/rest/server.php" \
  --data-urlencode "wstoken=$MOODLE_WS_TOKEN" \
  --data-urlencode "wsfunction=core_webservice_get_site_info" \
  --data-urlencode "moodlewsrestformat=json"'
```

Resultado válido: HTTP 200 y una respuesta que incluya `username=edumonitor_sync`, `userid=8` y el release de Moodle. En capturas, oculta el token y cualquier secreto.

## 4. Dataset académico de demostración

La demostración validada contiene 25 cursos, 25 estudiantes por curso, 50 actividades, 1.250 entregas, 1.100 calificaciones y 1.250 estados de finalización. El usuario técnico debe tener 25 matrículas activas, desde `DEMO-01-01` hasta `DEMO-05-05`.

El curso canónico utilizado por EduMonitor es `201 → DEMO-01-01`; Moodle puede tener otro ID interno y Moodle Sync lo resuelve mediante `shortname`.

La rama que se entregue al ingeniero debe incluir los scripts y CSV del seed académico masivo. Si esos archivos no están en la rama, el README no puede reproducir por sí solo las 25 matrículas ni las calificaciones: primero hay que incorporar y revisar esos archivos en Git, sin incluir tokens, contraseñas ni datos reales.

Después del seed, la salida esperada es:

```text
Cursos procesados: 25
Actividades creadas: 50
Entregas nuevas detectadas: 1250
Calificaciones procesadas: 1100
Estados de finalización procesados: 1250
```

Una segunda ejecución puede informar `Actividades creadas: 0` porque el seed es idempotente.

## 5. Acceso de docentes

Auth crea los usuarios ficticios `docente1@edumonitor.test`, `docente2@edumonitor.test` y `admin@edumonitor.test`. La contraseña de demostración es el valor local de `AUTH_SEED_PASSWORD`, no una contraseña escrita en este README. El ingeniero debe recibirla por un canal privado o definir una nueva en su `.env`.

Para iniciar sesión contra el gateway:

```bash
curl -sS -X POST http://localhost:5000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"docente1@edumonitor.test","password":"VALOR_LOCAL_DE_AUTH_SEED_PASSWORD"}'
```

No guardes la respuesta completa si contiene el JWT. Usa el token solo en la sesión local de demostración.

## 6. Apagar y reanudar

```bash
docker compose stop
docker compose up -d
```

No utilices `docker compose down -v` salvo que quieras borrar los volúmenes, cursos, usuarios, calificaciones y tokens locales de Moodle.
