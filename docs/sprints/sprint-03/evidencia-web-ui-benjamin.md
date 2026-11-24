# Sprint 3 — Verificación final de web-ui (Benjamín)

**Estado:** código de cierre preparado. Los resultados automáticos se registran con `validar_todo.py`; las pruebas en celular, entorno completo y ensayo deben ejecutarse y registrarse.

## Cambios desarrollados y verificados en GitHub

- S3-33/S3-34/S3-35: PR #59 fusionado en `develop` el 23-11-2026. CI del PR: `verificar-repo` y `web-ui` correctas.
- Correcciones del cierre: estados vacíos ilustrados, adaptación de barra inferior y desplazamiento de tablas, movimiento reducido, textos de fechas del informe y paginación por curso.
- **No marcar como aprobados** los casos manuales sin ejecutarlos.

## S3-31 a S3-35 — Trabajo anterior

- S3-31: consultar las decisiones del equipo en `docs/sprints/sprint-03/README.md` y confirmarlas con Juan; el archivo no demuestra por sí solo la asistencia.
- S3-32: PR #52 fusionado, rediseño integrado.
- S3-33, S3-34, S3-35: PR #59 fusionado el 23/11; falta comprobar el informe con el entorno de demostración real.

## S3-36 — Prueba en teléfono real (anticipada desde 24 nov.)

Dispositivo: ______________. Navegador y versión: ______________. Resolución: __________.
Fecha/hora: __________. Persona que probó: __________. URL y entorno: ______________.

**Importante:** el teléfono debe usar la IP LAN del servidor, no `localhost` de la computadora. Si se ejecuta Vite con `npm run dev -- --host 0.0.0.0`, configurar `VITE_API_URL` y `VITE_AGENT_URL` con las direcciones LAN correctas y reiniciar Vite. No compartir contraseñas ni tokens.

| Flujo | Resultado (Pasa/Falla/No probado) | Hallazgo / evidencia |
|---|---|---|
| Inicio de sesión válido e inválido | No probado | |
| Lista de cursos y sincronización | No probado | |
| Dashboard: métricas, gráficos, lista y paginación | No probado | |
| Tabla horizontal a 320–390 px sin recortes de acciones | No probado | |
| Alertas: filtros, evidencia y ficha individual | No probado | |
| Chat / Edu: pregunta, respuesta y error controlado | No probado | |
| Informe HU-06: fecha, métricas, hallazgos y fuentes | No probado | |
| Barra inferior: área segura, táctil, orientación vertical | No probado | |
| Rotación horizontal y teclado móvil abierto | No probado | |

## S3-37 — Estados vacíos y movimiento reducido (24 nov.)

| Caso | Resultado | Evidencia |
|---|---|---|
| Cursos sin resultados y filtros sin coincidencias | No probado | |
| Dashboard sin estudiantes, notas o alertas | No probado | |
| Informe sin métricas o sin hallazgos | No probado | |
| Conexión interrumpida y botón Reintentar | No probado | |
| Preferencia de movimiento reducido activa | No probado | |
| Preferencia de movimiento reducido desactivada | No probado | |
| Consistencia de textos, espacios y transiciones | No probado | |

## S3-38 — Lista de verificación final (adelantada al 24 nov.)

- [ ] `npm.cmd ci` desde `services/web-ui`.
- [ ] `npm.cmd run test` pasa (registrar cantidad exacta de pruebas, no asumir).
- [ ] `npm.cmd run lint` sin errores.
- [ ] `npm.cmd run build` exitoso.
- [ ] CI de la PR de cierre y de `develop` en verde.
- [ ] Iniciar sesión, cursos, dashboard, alertas, ficha, informe y agente contra el entorno de demostración.
- [ ] Comprobar el informe de PRUEBA01 desde `/cursos/:id/informe` con datos no simulados.
- [ ] Verificar una nota cero, pendiente de calificar y sin entrega, sin confundirlos.
- [ ] Registrar defectos, responsable, corrección y repetición de prueba.

## S3-39 — Integración y ensayo (preparación anticipada el 24 nov.)

- [ ] Asistir a las pruebas integradas del equipo.
- [ ] Ejecutar el recorrido asignado en la demostración y coordinar con Gabriel/Juan.
- [ ] Registrar el resultado del ensayo y cualquier plan alternativo.

## Hallazgos y correcciones

| Fecha | Pantalla / dispositivo | Descripción | Cambio / PR | Reprueba |
|---|---|---|---|---|
| _pendiente_ | | | | |

## Pendientes no pertenecientes al código de web-ui

- Issue #12: tablero Scrum del Sprint 1; su cierre requiere comprobar épicas, responsables y acceso al tablero con el líder.
- PR #63 de Juan: rediseño del agente y login. Revisar por separado; no mezclar sus cambios con esta entrega sin aprobación.
