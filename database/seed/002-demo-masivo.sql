USE EduMonitor;
GO

-- Dataset opcional para la demostración: 5 docentes x 5 cursos x 25 estudiantes.
-- Es ficticio, repetible y usa IDs separados del dataset PRUEBA01.
DECLARE @courseNumber INT = 1;
WHILE @courseNumber <= 25
BEGIN
    DECLARE @courseId INT = 200 + @courseNumber;
    DECLARE @teacherNumber INT = ((@courseNumber - 1) / 5) + 1;
    DECLARE @groupNumber INT = ((@courseNumber - 1) % 5) + 1;
    DECLARE @shortName NVARCHAR(100) = CONCAT('DEMO-', FORMAT(@teacherNumber, '00'), '-', FORMAT(@groupNumber, '00'));
    DECLARE @fullName NVARCHAR(200) = CONCAT('Curso demo ', @teacherNumber, ', grupo ', @groupNumber);

    IF NOT EXISTS (SELECT 1 FROM sync.course WHERE course_id = @courseId)
        INSERT INTO sync.course(course_id, short_name, full_name, last_sync_at)
        VALUES (@courseId, @shortName, @fullName, SYSUTCDATETIME());

    DECLARE @studentNumber INT = 1;
    WHILE @studentNumber <= 25
    BEGIN
        DECLARE @studentId INT = 20000 + ((@courseNumber - 1) * 25) + @studentNumber;
        DECLARE @studentName NVARCHAR(200) = CONCAT('Estudiante Demo ', @courseNumber, '-', FORMAT(@studentNumber, '00'));
        DECLARE @email NVARCHAR(320) = CONCAT('demo', @courseNumber, '-', FORMAT(@studentNumber, '00'), '@example.test');

        IF NOT EXISTS (SELECT 1 FROM sync.student WHERE student_id = @studentId)
            INSERT INTO sync.student(student_id, full_name, email)
            VALUES (@studentId, @studentName, @email);

        IF NOT EXISTS (SELECT 1 FROM sync.grade WHERE course_id = @courseId AND student_id = @studentId AND activity_id = 1 AND sync_id = 'demo-masivo-1')
            INSERT INTO sync.grade(course_id, student_id, activity_id, activity_name, status, submission_status, score, max_score, sync_id, synced_at)
            VALUES (@courseId, @studentId, 1, 'Actividad demo 1', 'graded', 'submitted', CASE WHEN @studentNumber % 5 = 0 THEN 0 ELSE 6 + (@studentNumber % 5) END, 10, 'demo-masivo-1', SYSUTCDATETIME());

        IF NOT EXISTS (SELECT 1 FROM sync.grade WHERE course_id = @courseId AND student_id = @studentId AND activity_id = 2 AND sync_id = 'demo-masivo-1')
            INSERT INTO sync.grade(course_id, student_id, activity_id, activity_name, status, submission_status, score, max_score, sync_id, synced_at)
            VALUES (@courseId, @studentId, 2, 'Actividad demo 2', CASE WHEN @studentNumber % 4 = 0 THEN 'pending_grading' ELSE 'graded' END, 'submitted', CASE WHEN @studentNumber % 4 = 0 THEN NULL ELSE 5 + (@studentNumber % 6) END, 10, 'demo-masivo-1', SYSUTCDATETIME());

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
