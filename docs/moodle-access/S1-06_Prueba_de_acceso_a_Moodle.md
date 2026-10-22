# S1-06: Prueba de acceso a Moodle

**Responsable:** Mikel · **Fecha:** 20/10/2026 · **Estado:** borrador (hay puntos pendientes marcados con ⚠)

## 1. Entorno de prueba

| Dato | Valor |
|---|---|
| Moodle | **5.2.4 (Build 20261005)**, versión interna 2026042004 |
| Imagen Docker | `oksigenia/moodle:5.2` (las imágenes de Bitnami dejaron de actualizarse en agosto de 2025) |
| Base de datos | MariaDB 11.4 |
| URL local | http://localhost:8080 |
| Protocolo | REST con formato JSON |
| Servicio web | `EduMonitor` (solo usuarios autorizados) |

Los datos son ficticios. No se usan datos reales de estudiantes.

## 2. Datos de prueba

Curso `PRUEBA01` (id 2). Tarea 1 con nota máxima 10.

| Usuario | id | Rol | Situación en Tarea 1 |
|---|---|---|---|
| docente1 | 3 | Teacher | (usuario del token) |
| estudiante1 | 4 | Student | Calificado: 8 |
| estudiante2 | 5 | Student | Calificado: **0** |
| estudiante3 | 6 | Student | Entregado, **pendiente de calificar** |
| estudiante4 | 7 | Student | **Sin entrega** |
| estudiante5 | 8 | Student | Calificado: 5 |

## 3. Funciones probadas

Se usó el token de `docente1`, que **no es administrador** (`userissiteadmin: false`).

| # | Función | Resultado |
|---|---|---|
| 1 | `core_webservice_get_site_info` | OK |
| 2 | `core_enrol_get_users_courses` | OK |
| 3 | `core_enrol_get_enrolled_users` | OK |
| 4 | `gradereport_user_get_grade_items` | OK |
| 5 | `core_course_get_contents` | OK |
| 6 | `core_completion_get_activities_completion_status` | OK, pero devuelve `statuses` vacío porque la Tarea 1 no tiene seguimiento de finalización configurado. El error inicial `invalid_parameter_exception` se debió a un `userid` vacío en la llamada, no a Moodle. |
| 7 | `mod_assign_get_assignments` | OK |
| 8 | `mod_assign_get_submissions` | OK. Devuelve el estado de cada entrega (`status`, `gradingstatus`). |

## 4. Permisos

- Primer intento con el token: `accessexception`. Causa: el usuario no tenía el permiso `webservice/rest:use`.
- Solución en esta instancia de pruebas: permitir `webservice/rest:use` al rol *Authenticated user*.
- ⚠ Para el sistema real conviene un rol dedicado a servicios web.
- La pantalla de tokens muestra una advertencia de capacidad faltante `moodle/user:update`. No impidió ninguna de las llamadas 1 a 5. No se concede, porque el sistema no modifica datos de Moodle.

## 5. Escalas de calificación

- La Tarea 1 usa una escala **numérica 0 a 10** (`grademin` 0, `grademax` 10, `scaleid` null).
- El total del curso usa la misma escala.
- Los campos `gradeformatted` y `percentageformatted` llegan como **texto** (`"8.00"`, `"80.00 %"`). El campo `rangeformatted` trae una entidad HTML (`0&ndash;10`). Se debe calcular con `graderaw`, `grademin` y `grademax`, no con los campos de texto.
- ⚠ La escala 0 a 100 todavía no se ha probado (falta crear un cuestionario).

## 6. Cómo distingue Moodle los estados de calificación (para S1-09)

Valores devueltos por `gradereport_user_get_grade_items` en el ítem de la Tarea 1:

| Situación | `graderaw` | `gradeformatted` | Otros campos |
|---|---|---|---|
| Nota normal (8 ó 5) | número | `"8.00"` | `gradedategraded` con fecha |
| **Nota cero** | **0** | `"0.00"` | `gradedategraded` con fecha |
| **Pendiente de calificar** | `null` | `"-"` | `status: "novalue"`, `gradedatesubmitted` con fecha |
| **Sin entrega** | `null` | `"-"` | sin `status`, sin fechas |

Conclusiones:
1. **Nota cero se distingue bien** de las demás, porque `graderaw` es 0 y no `null`.
2. **"Sin entrega" y "pendiente de calificar" tienen ambos `graderaw` null** en `gradereport_user_get_grade_items`, así que esa función sola no basta. Se resuelven combinándola con `mod_assign_get_submissions`:

   | Situación | En `mod_assign_get_submissions` | `graderaw` |
   |---|---|---|
   | Nota normal | `status: "submitted"`, `gradingstatus: "graded"` | número |
   | **Nota cero** | `status: "submitted"`, `gradingstatus: "graded"` | **0** |
   | **Pendiente de calificar** | `status: "submitted"`, `gradingstatus: "notgraded"` | `null` |
   | **Sin entrega** | **el estudiante no aparece en la lista** | `null` |

   Regla para el sistema: *sin entrega* = estudiante matriculado con rol Student que no aparece en las entregas de esa tarea.
   ⚠ No probado: un estudiante con entrega en borrador (`status` distinto de `submitted`). Se probará en el Sprint 2.
3. Un `graderaw` null **no** debe contarse como 0 en ningún indicador.

### Identificador de estudiantes

`core_enrol_get_enrolled_users`, consultada con el token del docente, devuelve a los estudiantes con `id`, `fullname` y `email`, pero **con el campo `username` vacío**. El propio docente sí lo trae.

Decisión para el sistema: identificar a cada estudiante por su **`id` de Moodle**, que es estable y coincide en todas las funciones (`gradereport_user_get_grade_items` usa el mismo `userid`). No usar `username` como clave. Si el sistema necesita un dato de respaldo, `email` está disponible. ⚠ Confirmar con Gabriel que la clave del modelo de datos sea el `id` de Moodle.

## 7. Datos no disponibles o pendientes

- Finalización de actividades: el sitio la tiene activa (`enablecompletion: 1`) y la función responde, pero solo devuelve datos de las actividades que tienen el seguimiento configurado. Con la Tarea 1 sin configurar devuelve una lista vacía. Regla para el sistema: lista vacía significa "dato no disponible", no "0 % completado".
- ⚠ Pendiente: configurar *Activity completion* en la Tarea 1 y repetir la prueba para comprobar que devuelve datos reales.
- Estado de entregas: resuelto con `mod_assign_get_submissions` (ver sección 6).
- Privacidad: `mod_assign_get_submissions` devuelve también el **texto completo de lo que escribió cada estudiante** (`onlinetext`). El servicio de sincronización solo debe guardar `userid`, `status`, `gradingstatus` y las fechas, y descartar el contenido de la entrega.

## 8. Evidencia

- Carpeta `evidencia/` con las respuestas JSON de las 8 llamadas. En `1_site_info.json` el campo `userprivateaccesskey` está reemplazado por `REDACTED`.
- `EduMonitor_Moodle_Postman.json`: colección con las mismas 8 llamadas. Las pruebas de esta tarea se ejecutaron con PowerShell (`Invoke-RestMethod`) y no con Postman; la colección contiene las mismas llamadas para repetirlas. El token va solo en la variable `token` (Current value) y nunca en el repositorio.
