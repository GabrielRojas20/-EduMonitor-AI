# Sprint 3 · Guion de la parte de Benjamín (web-ui)

**Estado:** propuesta para ensayo. El equipo debe acordar el orden de intervención; esta guía no registra una reunión celebrada.

## Antes de exponer

1. El equipo mantiene disponible el gateway, auth-courses, analytics, agente y Moodle o su entorno de prueba.
2. Se valida el login del docente de prueba y se abre un curso PRUEBA01 o uno de los cursos ficticios cargados.
3. Se deja abierto el navegador en pantalla completa y, si se usa un celular, en la misma red local.
4. Se prepara plan B con captura o vídeo autorizado por Gabriel: si hay corte de servicios, no inventar respuestas.

## Intervención (2–3 minutos)

**Inicio (15 s).** «Mi responsabilidad fue la interfaz web de EduMonitor AI. En el Sprint 3 cerré errores técnicos, añadí pruebas automatizadas y completé la visualización del informe académico HU-06. También trabajé la experiencia móvil y los estados vacíos».

**Cursos y dashboard (30–40 s).** «Después de iniciar sesión, el docente ve únicamente sus cursos. Aquí se muestran los indicadores, el estado de sincronización y la información de estudiantes. La interfaz distingue una nota cero real de un dato que todavía no está disponible; esto evita presentar conclusiones incorrectas».

**Informe académico HU-06 (40–50 s).** «Desde el dashboard abrimos Ver informe. La pantalla consume el informe de Analytics y presenta métricas, fecha del corte de indicadores, hallazgos y fuentes. Las fechas de primera y última observación no se presentan equivocadamente como fechas del período académico. Si no hay métricas o hallazgos, se muestra un estado vacío explicativo».

**Alertas y agente (20–30 s).** «Las alertas incluyen severidad, regla, evidencia y acceso a la ficha del estudiante. El asistente IA presenta la información del curso mediante las herramientas disponibles; las respuestas son del servicio, no textos inventados por el navegador». (Si se integró el PR #63, el agente aparece dentro del curso; en caso contrario, usar la sección Agente IA existente).

**Calidad y cierre (30–40 s).** «La interfaz cuenta con pruebas de Vitest y Testing Library; comprobamos validaciones y errores de la API, estados de pantalla y la página del informe. La validación final se apoya en el resultado registrado de `npm run test`, `npm run lint` y `npm run build`, más una prueba manual en teléfono real». Mencionar **solo la cantidad de pruebas que aparezca realmente en la ejecución final**.

**Cierre (10 s).** «La interfaz está conectada a los servicios del proyecto y queda lista para la demostración integrada después de que los controles y ensayos sean aprobados por el equipo».

## Recorrido corto en el navegador

1. `/login`: envío válido; demostrar que un correo incorrecto se rechaza.
2. `/cursos`: lista, búsqueda, sincronización o estados (sin enviar una sincronización si el docente de demo no lo autorizó).
3. `/cursos/:id`: tarjetas, gráficos y tabla, buscar estudiante y cambiar página.
4. `/cursos/:id/estudiantes/:sid`: ficha con notas y evidencias.
5. `/alertas?curso=:id`: detalle de una alerta y su fuente.
6. `/cursos/:id/informe`: métricas, fechas, hallazgos y fuentes.
7. Chat: nueva ubicación dentro del curso si el PR #63 está integrado; de lo contrario, navegación anterior.
8. Mostrar ancho móvil y estado vacío con la ilustración, y alternar la preferencia de movimiento reducido.

## Acciones ante problemas durante la demostración

- **El agente no responde:** mostrar estado de error y comentar la dependencia del servicio; no simular una respuesta verdadera.
- **El curso carece de datos:** explicar “No disponible” frente a cero y usar el curso de prueba acordado.
- **No carga el gateway:** avisar al equipo y continuar con material de respaldo real aprobado, sin afirmar que hubo integración exitosa.
- **Falla de red o móvil:** continuar en escritorio y adjuntar el resultado del teléfono obtenido previamente.

## Evidencia pendiente que debe registrarse con datos reales

- Dispositivo, navegador, fecha, flujo, resultado y capturas de S3-36.
- Comandos y salidas reales de S3-38 en `evidencia-automatica-webui-benjamin.md`.
- Hora, integrantes presentes, pantallas ensayadas y fallos/repruebas de S3-39.
