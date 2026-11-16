# Datos de demostración PRUEBA01

## Curso

- Curso: Metodologías Ágiles
- Short name: PRUEBA01
- ID utilizado en el entorno local: 2
- Datos ficticios basados en el sílabo de Metodologías Ágiles.

## Contenido

El backup incluye:

- secciones y actividades del curso;
- estudiantes ficticios;
- roles de los usuarios;
- archivos y recursos;
- entregas;
- calificaciones;
- estados de finalización;
- datos necesarios para la demostración de Moodle Sync.

## Restauración

1. Levantar el entorno con Docker Compose.
2. Entrar en `http://localhost:8080`.
3. Iniciar sesión con el administrador local.
4. Ir a `Site administration > Courses > Restore course`.
5. Subir el archivo `PRUEBA01-demo.mbz`.
6. Elegir `Restore as a new course`.
7. Seleccionar una categoría.
8. Restaurar el curso con un nombre diferente si `PRUEBA01` ya existe.
9. Verificar las actividades, estudiantes y calificaciones.
10. Configurar el servicio web `EduMonitor`.
11. Guardar el token únicamente en `.env`.
12. Ejecutar la sincronización desde EduMonitor.

## Seguridad

Los usuarios incluidos son ficticios. No se incluyen datos reales de estudiantes.

El archivo `.env`, el token de Moodle, las contraseñas y los JWT no forman parte del repositorio.
