USE EduMonitor;
GO

-- Dataset opcional para la demostración: 5 docentes x 5 cursos x 25 estudiantes.
-- Es ficticio, repetible y usa IDs separados del dataset PRUEBA01.
DECLARE @courseNumber INT = 1;
    DECLARE @CourseNames TABLE (course_number INT PRIMARY KEY, full_name NVARCHAR(200));
    INSERT INTO @CourseNames VALUES
        (1, N'08080113 - Física'),
        (2, N'08080114 - Álgebra Lineal'),
        (3, N'08080115 - Cálculo Diferencial'),
        (4, N'08080116 - Algoritmos y Lógica de Programación'),
        (5, N'08080117 - Lógica Matemática'),
        (6, N'08080201 - Fundamentos de Ingeniería de Software'),
        (7, N'08080202 - Programación Orientada a Objetos'),
        (8, N'08080203 - Sistemas Operativos'),
        (9, N'08080204 - Metodología de la Investigación'),
        (10, N'08080205 - Métodos Numéricos'),
        (11, N'08080206 - Estructura de Datos'),
        (12, N'08080207 - Probabilidad y Estadística'),
        (13, N'08080208 - Modelamiento y Diseño de Software'),
        (14, N'08080209 - Introducción a Redes'),
        (15, N'08080210 - Metodologías Ágiles'),
        (16, N'08080211 - Redes'),
        (17, N'08080212 - Base de Datos'),
        (18, N'08080213 - Investigación Operativa'),
        (19, N'08080214 - Patrones de Software'),
        (20, N'08080215 - Calidad de Software'),
        (21, N'08080216 - Ingeniería de Requisitos'),
        (22, N'08080217 - Arquitectura de Software'),
        (23, N'08080218 - Seguridad Informática'),
        (24, N'08080219 - Desarrollo Web'),
        (25, N'08080220 - Gestión de Proyectos');
    DECLARE @StudentNames TABLE (student_number INT PRIMARY KEY, full_name NVARCHAR(200));
    INSERT INTO @StudentNames VALUES
        (1, N'Ana Sofía Acosta Molina'),
        (2, N'Bruno Benítez Paredes'),
        (3, N'Camila Cabrera Ruiz'),
        (4, N'Diego Delgado Vera'),
        (5, N'Elena Escobar León'),
        (6, N'Fabián Fernández Soto'),
        (7, N'Gabriela García Mena'),
        (8, N'Héctor Herrera Paz'),
        (9, N'Isabela Ibarra Cruz'),
        (10, N'Javier Jiménez Lara'),
        (11, N'Karina Kuri Salazar'),
        (12, N'Leonardo López Vela'),
        (13, N'Mariana Martínez Gil'),
        (14, N'Nicolás Naranjo Ortiz'),
        (15, N'Olivia Ortega Silva'),
        (16, N'Pablo Paredes Ríos'),
        (17, N'Renata Quintero Mora'),
        (18, N'Sebastián Ramírez Luna'),
        (19, N'Tamara Salas Torres'),
        (20, N'Ulises Suárez Vega'),
        (21, N'Valentina Torres Cedeño'),
        (22, N'William Ulloa Reyes'),
        (23, N'Ximena Vargas Peña'),
        (24, N'Yamil Yánez Flores'),
        (25, N'Zoe Zambrano Castro');
WHILE @courseNumber <= 25
BEGIN
    DECLARE @courseId INT = 200 + @courseNumber;
    DECLARE @teacherNumber INT = ((@courseNumber - 1) / 5) + 1;
    DECLARE @groupNumber INT = ((@courseNumber - 1) % 5) + 1;
    DECLARE @shortName NVARCHAR(100) = CONCAT('DEMO-', FORMAT(@teacherNumber, '00'), '-', FORMAT(@groupNumber, '00'));
    DECLARE @fullName NVARCHAR(200) = (SELECT full_name FROM @CourseNames WHERE course_number = @courseNumber);

    IF NOT EXISTS (SELECT 1 FROM sync.course WHERE course_id = @courseId)
        INSERT INTO sync.course(course_id, short_name, full_name, last_sync_at)
        VALUES (@courseId, @shortName, @fullName, SYSUTCDATETIME());

    DECLARE @studentNumber INT = 1;
    WHILE @studentNumber <= 25
    BEGIN
        DECLARE @studentId INT = 20000 + ((@courseNumber - 1) * 25) + @studentNumber;
        DECLARE @studentName NVARCHAR(200) = (SELECT full_name FROM @StudentNames WHERE student_number = @studentNumber);
        DECLARE @email NVARCHAR(320) = CONCAT('demo', @courseNumber, '-', FORMAT(@studentNumber, '00'), '@example.test');

        IF NOT EXISTS (SELECT 1 FROM sync.student WHERE student_id = @studentId)
            INSERT INTO sync.student(student_id, full_name, email)
            VALUES (@studentId, @studentName, @email);

        IF NOT EXISTS (SELECT 1 FROM sync.grade WHERE course_id = @courseId AND student_id = @studentId AND activity_id = 1 AND sync_id = 'demo-masivo-1')
            INSERT INTO sync.grade(course_id, student_id, activity_id, activity_name, status, submission_status, score, max_score, sync_id, synced_at)
            VALUES (@courseId, @studentId, 1, CONCAT(@fullName, ' - ', CASE @courseNumber % 5 WHEN 1 THEN 'Laboratorio y fundamentos' WHEN 2 THEN 'Ejercicios y análisis' WHEN 3 THEN 'Aplicación práctica' WHEN 4 THEN 'Proyecto de curso' ELSE 'Informe de aprendizaje' END), 'graded', 'submitted', CASE WHEN @studentNumber % 5 = 0 THEN 0 ELSE 6 + (@studentNumber % 5) END, 10, 'demo-masivo-1', SYSUTCDATETIME());

        IF NOT EXISTS (SELECT 1 FROM sync.grade WHERE course_id = @courseId AND student_id = @studentId AND activity_id = 2 AND sync_id = 'demo-masivo-1')
            INSERT INTO sync.grade(course_id, student_id, activity_id, activity_name, status, submission_status, score, max_score, sync_id, synced_at)
            VALUES (@courseId, @studentId, 2, CONCAT(@fullName, ' - ', CASE @courseNumber % 5 WHEN 1 THEN 'Tarea de consolidación' WHEN 2 THEN 'Resolución de problemas' WHEN 3 THEN 'Práctica evaluada' WHEN 4 THEN 'Entrega final' ELSE 'Evaluación aplicada' END), CASE WHEN @studentNumber % 4 = 0 THEN 'pending_grading' ELSE 'graded' END, 'submitted', CASE WHEN @studentNumber % 4 = 0 THEN NULL ELSE 5 + (@studentNumber % 6) END, 10, 'demo-masivo-1', SYSUTCDATETIME());

        IF NOT EXISTS (SELECT 1 FROM sync.completion WHERE course_id = @courseId AND student_id = @studentId AND activity_id = 1 AND sync_id = 'demo-masivo-1')
            INSERT INTO sync.completion(course_id, student_id, activity_id, state, sync_id, observed_at)
            VALUES (@courseId, @studentId, 1, CASE WHEN @studentNumber % 6 = 0 THEN 'incomplete' ELSE 'complete' END, 'demo-masivo-1', SYSUTCDATETIME());

        IF NOT EXISTS (SELECT 1 FROM sync.completion WHERE course_id = @courseId AND student_id = @studentId AND activity_id = 2 AND sync_id = 'demo-masivo-1')
            INSERT INTO sync.completion(course_id, student_id, activity_id, state, sync_id, observed_at)
            VALUES (@courseId, @studentId, 2, CASE WHEN @studentNumber % 4 = 0 THEN 'incomplete' ELSE 'complete' END, 'demo-masivo-1', SYSUTCDATETIME());

        SET @studentNumber += 1;
    END;

    SET @courseNumber += 1;
END;
GO
