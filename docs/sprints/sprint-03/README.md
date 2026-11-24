# Sprint 3: Informe del curso, deuda técnica y cierre del proyecto

**Fechas:** del lunes 16 al jueves 26 de noviembre de 2026 (presentación final el jueves 26).

**Estado:** en curso

**Objetivo:** Cerrar la deuda técnica del Sprint 2, entregar la historia HU-06 (informe del curso) y dejar el sistema integrado, probado y documentado para la demostración final.

**Entregable:** El sistema integrado en `develop` con las siete historias de usuario, la evaluación final del agente con su reporte de métricas, el manual del agente, el README de instalación, la documentación final, el video de respaldo y la presentación.

## Roles del sprint

| Rol | Responsable |
|---|---|
| Facilitador del sprint | Juan |
| Responsable de la demostración | Gabriel |
| Responsable del repositorio | Gabriel |
| Responsable de la documentación | Juan |

## Puntos de control

| Fecha y hora | Condición |
|---|---|
| Lunes 16, 22:00 | El trabajo de Mikel y de Gabriel está en `develop` |
| Viernes 20, 22:00 | Deuda técnica cerrada e informe (HU-06) de punta a punta con datos de prueba |
| Martes 24, 22:00 | Todo integrado y video de respaldo grabado |
| Miércoles 25, 11:00 | Congelamiento de código: solo se fusionan correcciones de errores aprobadas por Gabriel |

## Tareas por integrante

El detalle de cada actividad (pasos, días y criterio de terminado) está en el documento de planificación del Sprint 3. Los estados son los que muestra `develop` al 24 de noviembre.

**Juan**
- [x] S3-04 Evaluación contra el gateway real con el curso PRUEBA01 (PR #57)
- [x] S3-05 Informe del agente con la evidencia de cada alerta (PR #61, en revisión)
- [x] S3-06 Nombres reales de actividades y `listar_cursos` sin consultas adicionales (PR #61, en revisión)
- [x] S3-02 Las preguntas de progreso y «cómo va» reciben interpretación y recomendación
- [x] S3-03 Escenario de evaluación de «calificaciones pendientes»
- [x] S3-07 Escenarios del informe con datos reales
- [x] S3-08 Evaluación final contra el gateway real y reporte de métricas (`evaluation/agent-scenarios/reportes/`)
- [x] S3-09 Preguntas de la demostración y manual del agente (`docs/agent-design/manual-del-agente.md`)
- [ ] S3-10 Documento del Sprint 3 y documentación final
- [ ] S3-11 Ensayo general y video de respaldo

**Mikel**
- [x] S3-13 Curso PRUEBA01 reproducible en `docs/demo` (PR #53)
- [x] S3-14 Conteo de estudiantes y última sincronización en la lista de cursos (PR #54)
- [x] S3-15 Nombre real de las actividades (PR #55)
- [x] S3-16 Historial de auditoría de las sincronizaciones (PR #58)
- [ ] S3-17 Decisión sobre los servicios separados
- [ ] S3-18 Apoyo a la evaluación con datos reales
- [ ] S3-19 Pruebas de permisos e integración
- [ ] S3-20 README de instalación
- [ ] S3-21 Guion y entorno de la demostración
- [ ] S3-22 Pruebas finales de los servicios

**Gabriel**
- [x] S3-25 Pruebas de analytics ampliadas (PR #56)
- [x] S3-26 Informe del curso: cálculo y endpoint, con valor observado, umbral y fuentes (PR #56)
- [x] S3-27 Pruebas de la interfaz en la integración continua (PR #56)
- [x] Corrección de analytics para usar solo la sincronización más reciente (PR #60)
- [x] Dataset masivo de demostración: 5 docentes, 25 cursos y 25 estudiantes por curso (PR #60)
- [ ] S3-28 Ajuste de reglas con el Product Owner
- [ ] S3-29 Prueba de carga con el dataset final
- [ ] S3-30 Pruebas finales y congelamiento de código

**Benjamín**
- [x] S3-32 Rediseño de la interfaz (PR #52)
- [x] S3-33 Pruebas automáticas de la interfaz (PR #59)
- [x] S3-34 ESLint, numeración de `basedOn` y favicon (PR #59)
- [x] S3-35 Pantalla del informe del curso (PR #59)
- [ ] S3-36 Prueba en celular real
- [ ] S3-37 Estados vacíos y pulido final
- [ ] S3-38 Pruebas finales de la interfaz

## Entrega final

La especificación del proyecto pide, además del código, el siguiente material. Cada integrante prepara su parte:

- [ ] Matriz de cumplimiento de requisitos funcionales y no funcionales actualizada (`docs/requirements/requisitos.md`)
- [ ] Registro de contribuciones por integrante
- [ ] Evidencias de pruebas reunidas en un solo lugar
- [ ] Guía de uso del sistema completo
- [ ] Diagrama de arquitectura, esquema de base de datos y listado de endpoints revisados
- [ ] Revisión y retrospectiva del sprint (`revision-y-retrospectiva.md`) y acta del Product Owner (`docs/product-owner/`)

## Dónde van los entregables

Carpetas principales: `services/`, `database/`, `docs/`, `evaluation/agent-scenarios/` y `docker-compose.yml`.

Cada tarea entra por pull request revisada por otra persona (ver `CONTRIBUTING.md`).
