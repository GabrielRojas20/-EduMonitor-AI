IF DB_ID(N'EduMonitor') IS NULL CREATE DATABASE EduMonitor;
GO
USE EduMonitor;
GO
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'sync') EXEC('CREATE SCHEMA sync');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'analytics') EXEC('CREATE SCHEMA analytics');
GO
IF OBJECT_ID('sync.course','U') IS NULL CREATE TABLE sync.course (course_id INT NOT NULL PRIMARY KEY, short_name NVARCHAR(100) NOT NULL, full_name NVARCHAR(200) NOT NULL, last_sync_at DATETIME2 NULL);
IF OBJECT_ID('sync.student','U') IS NULL CREATE TABLE sync.student (student_id INT NOT NULL PRIMARY KEY, full_name NVARCHAR(200) NOT NULL, email NVARCHAR(320) NULL);
IF OBJECT_ID('sync.grade','U') IS NULL CREATE TABLE sync.grade (grade_id INT IDENTITY PRIMARY KEY, course_id INT NOT NULL, student_id INT NOT NULL, activity_id INT NOT NULL, status NVARCHAR(30) NOT NULL, submission_status NVARCHAR(30) NOT NULL, score DECIMAL(8,3) NULL, max_score DECIMAL(8,3) NOT NULL, sync_id NVARCHAR(80) NOT NULL, synced_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME());
IF OBJECT_ID('sync.completion','U') IS NULL CREATE TABLE sync.completion (completion_id INT IDENTITY PRIMARY KEY, course_id INT NOT NULL, student_id INT NOT NULL, activity_id INT NOT NULL, state NVARCHAR(30) NOT NULL, sync_id NVARCHAR(80) NOT NULL, observed_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME());
IF OBJECT_ID('analytics.alert_rule','U') IS NULL CREATE TABLE analytics.alert_rule (rule_code NVARCHAR(50) PRIMARY KEY, name NVARCHAR(200) NOT NULL, metric NVARCHAR(50) NOT NULL, operator NVARCHAR(5) NOT NULL, threshold DECIMAL(8,3) NULL, severity NVARCHAR(20) NOT NULL, enabled BIT NOT NULL DEFAULT 1, updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME());
IF OBJECT_ID('analytics.alert','U') IS NULL CREATE TABLE analytics.alert (alert_id NVARCHAR(80) PRIMARY KEY, course_id INT NOT NULL, student_id INT NULL, rule_code NVARCHAR(50) NOT NULL, severity NVARCHAR(20) NOT NULL, status NVARCHAR(20) NOT NULL, detected_at DATETIME2 NOT NULL, resolved_at DATETIME2 NULL);
IF OBJECT_ID('analytics.alert_evidence','U') IS NULL CREATE TABLE analytics.alert_evidence (evidence_id NVARCHAR(80) PRIMARY KEY, alert_id NVARCHAR(80) NOT NULL, metric NVARCHAR(50) NOT NULL, observed_value DECIMAL(8,3) NULL, threshold DECIMAL(8,3) NULL, source_id NVARCHAR(80) NULL, explanation NVARCHAR(1000) NOT NULL);
GO
MERGE analytics.alert_rule AS target USING (VALUES
 ('LOW_AVERAGE','Promedio bajo','averageScore10','lt',6.0,'warning',1),
 ('LOW_SUBMISSION','Baja entrega','submissionRate','lt',80.0,'warning',1),
 ('LOW_COMPLETION','Baja finalización','completionRate','lt',70.0,'warning',1),
 ('PENDING_GRADING','Pendientes de calificar','pendingGradingRate','gt',20.0,'info',1),
 ('NO_DATA','Datos insuficientes','completionRate','eq',NULL,'info',1)
) AS source(rule_code,name,metric,operator,threshold,severity,enabled)
ON target.rule_code = source.rule_code
WHEN MATCHED THEN UPDATE SET name=source.name, metric=source.metric, operator=source.operator, threshold=source.threshold, severity=source.severity, enabled=source.enabled
WHEN NOT MATCHED THEN INSERT(rule_code,name,metric,operator,threshold,severity,enabled) VALUES(source.rule_code,source.name,source.metric,source.operator,source.threshold,source.severity,source.enabled);
GO
INSERT INTO sync.course(course_id,short_name,full_name,last_sync_at) SELECT 101,'BD-4B','Bases de Datos 4B',SYSUTCDATETIME() WHERE NOT EXISTS (SELECT 1 FROM sync.course WHERE course_id=101);
INSERT INTO sync.course(course_id,short_name,full_name,last_sync_at) SELECT 102,'MET-4B','Metodologías Ágiles 4B',SYSUTCDATETIME() WHERE NOT EXISTS (SELECT 1 FROM sync.course WHERE course_id=102);
INSERT INTO sync.student(student_id,full_name,email) SELECT 1001,'Estudiante Uno','student1001@example.test' WHERE NOT EXISTS (SELECT 1 FROM sync.student WHERE student_id=1001);
INSERT INTO sync.student(student_id,full_name,email) SELECT 1002,'Estudiante Dos','student1002@example.test' WHERE NOT EXISTS (SELECT 1 FROM sync.student WHERE student_id=1002);
INSERT INTO sync.student(student_id,full_name,email) SELECT 1003,'Estudiante Tres','student1003@example.test' WHERE NOT EXISTS (SELECT 1 FROM sync.student WHERE student_id=1003);
INSERT INTO sync.grade(course_id,student_id,activity_id,status,submission_status,score,max_score,sync_id) SELECT 101,1001,201,'graded','submitted',8,10,'seed-1' WHERE NOT EXISTS (SELECT 1 FROM sync.grade WHERE course_id=101 AND student_id=1001 AND activity_id=201);
INSERT INTO sync.grade(course_id,student_id,activity_id,status,submission_status,score,max_score,sync_id) SELECT 101,1001,202,'graded','submitted',0,10,'seed-1' WHERE NOT EXISTS (SELECT 1 FROM sync.grade WHERE course_id=101 AND student_id=1001 AND activity_id=202);
INSERT INTO sync.grade(course_id,student_id,activity_id,status,submission_status,score,max_score,sync_id) SELECT 101,1002,201,'pending_grading','submitted',NULL,10,'seed-1' WHERE NOT EXISTS (SELECT 1 FROM sync.grade WHERE course_id=101 AND student_id=1002 AND activity_id=201);
INSERT INTO sync.grade(course_id,student_id,activity_id,status,submission_status,score,max_score,sync_id) SELECT 101,1002,202,'not_submitted','draft',NULL,10,'seed-1' WHERE NOT EXISTS (SELECT 1 FROM sync.grade WHERE course_id=101 AND student_id=1002 AND activity_id=202);
INSERT INTO sync.grade(course_id,student_id,activity_id,status,submission_status,score,max_score,sync_id) SELECT 101,1003,201,'graded','submitted',4,10,'seed-1' WHERE NOT EXISTS (SELECT 1 FROM sync.grade WHERE course_id=101 AND student_id=1003 AND activity_id=201);
INSERT INTO sync.completion(course_id,student_id,activity_id,state,sync_id) SELECT 101,1001,201,'complete','seed-1' WHERE NOT EXISTS (SELECT 1 FROM sync.completion WHERE course_id=101 AND student_id=1001 AND activity_id=201);
INSERT INTO sync.completion(course_id,student_id,activity_id,state,sync_id) SELECT 101,1002,201,'incomplete','seed-1' WHERE NOT EXISTS (SELECT 1 FROM sync.completion WHERE course_id=101 AND student_id=1002 AND activity_id=201);
INSERT INTO sync.completion(course_id,student_id,activity_id,state,sync_id) SELECT 101,1003,201,'not_available','seed-1' WHERE NOT EXISTS (SELECT 1 FROM sync.completion WHERE course_id=101 AND student_id=1003 AND activity_id=201);
GO
