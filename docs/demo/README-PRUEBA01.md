# Datos de demostración PRUEBA01

## Propósito

Este directorio contiene el backup Moodle reproducible del curso de demostración de EduMonitor AI. El curso utiliza datos completamente ficticios basados en el sílabo de Metodologías Ágiles.

Archivo incluido:

```text
PRUEBA01-demo.mbz
```

El backup contiene actividades con nombres reales, estudiantes ficticios, entregas, calificaciones y estados de finalización.

## Regla importante sobre el ID del curso

El archivo `.mbz` conserva el contenido y la configuración del curso, pero **no garantiza que Moodle conserve el mismo ID numérico** después de una restauración.

### Entorno actual de la demostración

En el entorno actual de EduMonitor, el curso original de prueba se identifica como:

```text
short name: PRUEBA01
ID: 2
```

Ese ID `2` solo debe utilizarse mientras el curso existente en Moodle conserve dicho ID.

### Restauración desde cero

Cuando el backup se restaura con la opción **Restore as a new course**, Moodle crea un curso nuevo y puede asignarle un ID diferente. En ese caso, el ID correcto para EduMonitor es el ID que Moodle muestre después de completar la restauración; no se debe asumir que será `2`.

Después de restaurar:

1. Abrir el curso restaurado en Moodle.
2. Confirmar que el short name sea `PRUEBA01` o actualizarlo al short name acordado.
3. Obtener el ID real desde la URL del curso, por ejemplo `course/view.php?id=7`, donde `7` sería el nuevo ID.
4. Usar ese ID real al configurar Auth Courses y al ejecutar Moodle Sync.
5. Crear o actualizar la relación del curso en Auth Courses con el mismo ID de Moodle.
6. Ejecutar la sincronización usando ese ID.
7. Verificar el estado con `GET /courses/{id}/sync` hasta obtener `succeeded`.

Ejemplo si Moodle asigna el ID `7`:

```text
Moodle: PRUEBA01 → ID 7
Auth Courses: curso con ID 7
Moodle Sync: POST /courses/7/sync
Estado: GET /courses/7/sync
```

No se debe restaurar sobre el curso existente con ID `2` si se quiere conservar el curso original. La restauración como curso nuevo es la opción recomendada para validar que el backup sea reproducible.

## Restauración paso a paso

1. Levantar el entorno con Docker Compose.
2. Entrar en `http://localhost:8080`.
3. Iniciar sesión con el administrador local.
4. Ir a `Site administration > Courses > Restore course`.
5. Subir `PRUEBA01-demo.mbz`.
6. Elegir `Restore as a new course`.
7. Seleccionar una categoría.
8. Completar la restauración.
9. Confirmar el short name y obtener el ID asignado por Moodle.
10. Verificar actividades, estudiantes, entregas, calificaciones y estados de finalización.
11. Configurar el servicio web `EduMonitor` y autorizar al usuario técnico.
12. Guardar el token únicamente en `.env`.
13. Registrar el mismo ID de Moodle en Auth Courses.
14. Ejecutar la sincronización con el ID real asignado.
15. Consultar el estado hasta que sea `succeeded`.

## Validación funcional

Con el ID real asignado por Moodle:

```bash
curl -i -X POST http://localhost:5002/courses/{MOODLE_COURSE_ID}/sync \
  -H "Authorization: Bearer $TOKEN_DOCENTE1"

curl -sS http://localhost:5002/courses/{MOODLE_COURSE_ID}/sync \
  -H "Authorization: Bearer $TOKEN_DOCENTE1"
```

La sincronización se considera correcta cuando la segunda respuesta contiene:

```json
"state":"succeeded"
```

## Alcance de este PR

Este PR agrega el backup `PRUEBA01-demo.mbz` y la documentación necesaria para restaurarlo y obtener el ID real asignado por Moodle.

Los cambios funcionales de `moodle-sync`, API Gateway, scripts de base de datos y `.env.example` deben revisarse en el PR de infraestructura o en el PR específico que los contenga. No se duplican aquí si ya fueron fusionados previamente en `develop`.

Para comprobar dónde están esos cambios:

```bash
git log --oneline --all -- docker-compose.yml
git log --oneline --all -- services/moodle-sync-service
git log --oneline --all -- services/api-gateway
git log --oneline --all -- .env.example
```

## Seguridad

Los usuarios incluidos son ficticios. No se incluyen datos reales de estudiantes.

No se versionan `.env`, tokens, contraseñas ni JWT. El token de Moodle debe configurarse únicamente en el entorno local.
