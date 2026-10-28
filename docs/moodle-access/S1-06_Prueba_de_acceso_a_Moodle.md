# S1-06: Prueba de acceso a Moodle

**Responsable:** Mikel · **Fecha:** 28/10/2026 · **Estado:** Actualizado (S1-06 resuelto)

## 1. Entorno de prueba

| Dato | Valor |
|---|---|
| Moodle | **5.2.4 (Build 20261005)**, versión interna 2026042004 |
| Imagen Docker | `oksigenia/moodle:5.2` |
| Base de datos | MariaDB 11.4 |
| URL local | http://localhost:8080 |
| Protocolo | REST con formato JSON |
| Servicio web | `EduMonitor` (solo usuarios autorizados) |

Los datos son estrictamente sintéticos de prueba. No se emplean datos reales ni texto de relleno en la extracción de entregas.

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
| 6 | `core_completion_get_activities_completion_status` | OK, pero devuelve `statuses` vacío porque la Tarea 1 no tiene seguimiento de finalización configurado. |
| 7 | `mod_assign_get_assignments` | OK |
| 8 | `mod_assign_get_submissions` | OK. Devuelve el estado de cada entrega (`status`, `gradingstatus`). |

## 4. Permisos

- Primer intento con el token: `accessexception`. Causa: el usuario no tenía el permiso `webservice/rest:use`.
- Solución en esta instancia de pruebas: permitir `webservice/rest:use` al rol *Authenticated user*.
- Para el sistema real conviene un rol dedicado a servicios web.
- La pantalla de tokens muestra una advertencia de capacidad faltante `moodle/user:update`. No impidió ninguna de las llamadas 1 a 5. No se concede, porque el sistema no modifica datos de Moodle.

## 5. Escalas de calificación

- La Tarea 1 usa una escala **numérica 0 a 10** (`grademin` 0, `grademax` 10, `scaleid` null).
- El total del curso usa la misma escala.
- Los campos `gradeformatted` y `percentageformatted` llegan como **texto** (`"8.00"`, `"80.00 %"`). El campo `rangeformatted` trae una entidad HTML (`0&ndash;10`). Se debe calcular con `graderaw`, `grademin` y `grademax`, no con los campos de texto.
- La escala **0 a 100** se probó con la Tarea 2 (`grademax` 100): Estudiante Dos con `graderaw` 90 y `gradeformatted` "90.00".
- Como hay actividades sobre 10 y sobre 100, los indicadores deben calcularse con `score / maxScore` (porcentaje) y no comparar notas crudas entre actividades.

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
2. **"Sin entrega" y "pendiente de calificar" tienen ambos `graderaw` null** en `gradereport_user_get_grade_items`, por lo que se combinan con `mod_assign_get_submissions`:

   | Situación | En `mod_assign_get_submissions` | `graderaw` |
   |---|---|---|
   | Nota normal | `status: "submitted"`, `gradingstatus: "graded"` | número |
   | **Nota cero** | `status: "submitted"`, `gradingstatus: "graded"` | **0** |
   | **Pendiente de calificar** | `status: "submitted"`, `gradingstatus: "notgraded"` | `null` |
   | **Sin entrega** | **el estudiante no aparece en la lista** | `null` |

   Regla para el sistema: *sin entrega* = estudiante matriculado con rol Student que no aparece en las entregas de esa tarea.

   Tabla completa de estados:

   | Situación | `status` de la entrega | `gradingstatus` | `graderaw` |
   |---|---|---|---|
   | Nota normal | `submitted` | `graded` | número |
   | Nota cero | `submitted` | `graded` | 0 |
   | Pendiente de calificar | `submitted` | `notgraded` | null |
   | **Borrador** | **`draft`** | `notgraded` | null |
   | Sin entrega | no aparece en la lista | no aplica | null |

3. Un `graderaw` null **no** debe contarse como 0 en ningún indicador.

### Identificador de estudiantes

`core_enrol_get_enrolled_users`, consultada con el token del docente, devuelve a los estudiantes con `id`, `fullname` y `email`.
Decisión para el sistema: identificar a cada estudiante por su **`id` de Moodle**, que es estable y coincide en todas las funciones.

## 7. Privacidad y tratamiento de contenido (onlinetext)

- **Eliminación de texto de relleno:** La función `mod_assign_get_submissions` retorna el campo de texto en línea (`onlinetext`). 
- **Regla de extracción en `moodle-sync`:** El servicio descarta el contenido textual de la entrega (`onlinetext`) y cualquier texto de relleno o borrador. Unicamente extrae y conserva los metadados estrictamente necesarios: `userid`, `status`, `gradingstatus`, notas y marcas temporales (`timecreated`, `timemodified`).

## 8. Decisiones de diseño

1. **Identificador del estudiante:** El `id` de Moodle como clave principal en todo el sistema.
2. **Exclusión de `onlinetext`:** El cliente `moodle-sync` valida explícitamente la ausencia de cadenas de texto no requeridas en el archivo de salida (`salida-curso-2.json`). La verificación en consola confirma que `Texto de las entregas (onlinetext) en la salida: no`.

## 9. Progreso de actividades (Activity completion)

Se configuró *Completion conditions* en la Tarea 1 y la Tarea 2 con los requisitos *Make a submission* y *Receive a grade*, llamando a `core_completion_get_activities_completion_status`:

| Estudiante | Tarea 1 (cmid 2) | Tarea 2 (cmid 3) |
|---|---|---|
| Uno (borrador en Tarea 2) | `state` 1 (completa) | `state` 0 (incompleta) |
| Dos (enviada y calificada) | `state` 1 (completa) | `state` 1 (completa) |

## 10. Evidencia

- **Salida JSON limpia (`salida-curso-2.json`):** Contiene únicamente las métricas de notas, fechas y estados de entrega sin incrustar texto plano ni rellenos *onlinetext*.
- **Validación de extracción:** La ejecución del binario de sincronización devuelve un estado de verificación de entrega sin filtración de contenidos textuales.
- **Colección de endpoints:** Archivos de prueba y respuestas JSON organizadas en la carpeta `evidencia/`.