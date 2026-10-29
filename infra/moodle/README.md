# Moodle local para pruebas (S1-05)

**Responsable:** Mikel

Instancia de Moodle en Docker para probar la sincronización de EduMonitor AI. Es solo para desarrollo y usa **datos ficticios**: no se cargan datos reales de estudiantes ni se suben secretos al repositorio. La evidencia de que funciona está en `docs/moodle-access/` (S1-06).

| Dato | Valor |
|---|---|
| Moodle | imagen `oksigenia/moodle:5.2` (la evidencia se tomó con 5.2.4) |
| Base de datos | MariaDB 11.4 |
| URL | http://localhost:8080 |
| Administrador | usuario `admin`, contraseña `MOODLE_ADMIN_PASSWORD` del `.env` |

## 1. Requisitos

Docker Desktop instalado y abierto (debe decir "Engine running").

## 2. Configurar las contraseñas

Desde esta carpeta (`infra/moodle`):

```bash
cp .env.example .env
```

Abre `.env` y cambia las tres contraseñas por otras tuyas. Moodle puede pedir una contraseña fuerte (mayúscula, minúscula, número y símbolo) y puede pedir cambiar la del administrador en el primer inicio. El archivo `.env` está en `.gitignore`: **no lo subas**.

## 3. Levantar Moodle

```bash
docker compose up -d
docker compose logs -f moodle
```

El primer arranque instala Moodle y tarda unos minutos. Cuando los registros dejen de avanzar, sal con `Ctrl+C` y abre http://localhost:8080.

## 4. Datos de prueba (ficticios)

Todo se hace desde la web de Moodle, entrando como `admin`.

### 4.1 Curso y usuarios

1. Crea el curso: nombre `Curso de Prueba EduMonitor`, nombre corto **`PRUEBA01`** (el CSV usa ese nombre corto).
2. Copia `usuarios.csv.example` como `usuarios.csv` y reemplaza `CAMBIAR-CLAVE` por una contraseña que cumpla la política de Moodle. `usuarios.csv` no se sube al repositorio.
3. En **Site administration → Users → Accounts → Upload users**, sube `usuarios.csv`. En los ajustes elige *Add new only, skip existing users*, *New user password: Field required in file* y *Force password change: No*.
4. En el curso, abre **Participants** y confirma 1 docente y 5 estudiantes. Quita al usuario `admin` de los participantes para que no aparezca como docente en los datos sincronizados (sigue siendo administrador del sitio).

### 4.2 Actividades

Crea dos tareas con **Add an activity → Assignment**, con *Online text* como único tipo de entrega y *Activity completion* configurado en **Completion conditions** con los requisitos *Make a submission* y *Receive a grade*.

| Tarea | Ajustes especiales |
|---|---|
| Tarea 1 | Nota máxima 10 |
| Tarea 2 | Nota máxima 100 y *Require students to click the submit button: Yes* (así existe el estado de borrador) |

Deja a los estudiantes en estas situaciones (en **View all submissions** el docente puede entregar y calificar por ellos):

| Estudiante | Tarea 1 | Tarea 2 |
|---|---|---|
| 1 | Calificado: 8 | Borrador (no enviado) |
| 2 | Calificado: 0 | Enviado y calificado: 90 |
| 3 | Enviado, sin calificar | Sin entrega |
| 4 | Sin entrega | Sin entrega |
| 5 | Calificado: 5 | Sin entrega |

## 5. Servicio web y token

1. **Site administration → General → Advanced features**: activa *Enable web services*.
2. **Server → Web services → Manage protocols**: habilita **REST**.
3. Permisos: para esta instancia de pruebas, permite `webservice/rest:use` al rol *Authenticated user* (**Users → Permissions → Define roles**). En un sistema real conviene un rol propio solo para servicios web.
4. **Server → Web services → External services → Add**: nombre `EduMonitor`, marca *Enabled* y *Authorised users only*.
5. Agrega estas funciones al servicio (**Functions → Add functions**):
   - `core_webservice_get_site_info`
   - `core_enrol_get_users_courses`
   - `core_enrol_get_enrolled_users`
   - `gradereport_user_get_grade_items`
   - `core_course_get_contents`
   - `core_completion_get_activities_completion_status`
   - `mod_assign_get_assignments`
   - `mod_assign_get_submissions`
6. En **Authorised users** del servicio agrega a `docente1`.
7. **Manage tokens → Create token**: usuario `docente1`, servicio `EduMonitor`. Copia el token en el momento: Moodle no lo vuelve a mostrar.

**El token es un secreto.** Guárdalo en un archivo fuera del repositorio o en tu `.env` local; nunca en el código, en capturas ni en la evidencia. Todos los servicios son de solo lectura: ninguna función de la lista modifica datos de Moodle.

## 6. Comprobar que funciona

Con el token en una variable de entorno de tu terminal (Git Bash):

```bash
export MOODLE_TOKEN="pega-aqui-tu-token"
curl -s -X POST http://localhost:8080/webservice/rest/server.php \
  -d wstoken=$MOODLE_TOKEN \
  -d wsfunction=core_webservice_get_site_info \
  -d moodlewsrestformat=json
```

La respuesta debe incluir `"username":"docente1"` y la versión de Moodle (`release`). Si responde `accessexception`, revisa el permiso del paso 5.3 y que `docente1` esté autorizado en el servicio.

## 7. Apagar, reanudar y borrar

```bash
docker compose stop        # apagar sin perder datos
docker compose up -d       # volver a encender
docker compose down -v     # PELIGRO: borra el curso, los usuarios y el token
```

Los datos viven en volúmenes de Docker: apagar el PC no los pierde. Solo `down -v` los elimina.
