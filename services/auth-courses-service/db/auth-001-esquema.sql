-- Esquema auth (propuesta de Mikel, a confirmar con Gabriel antes de usarlo con SQL Server).
-- Coincide con el modelo de services/auth-courses-service (AuthDb.cs).
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'auth') EXEC('CREATE SCHEMA auth');
GO

IF OBJECT_ID('auth.Users') IS NULL
CREATE TABLE auth.Users (
    Id           INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    Email        NVARCHAR(256) NOT NULL,
    Name         NVARCHAR(200) NOT NULL,
    Role         NVARCHAR(20)  NOT NULL,
    PasswordHash NVARCHAR(500) NOT NULL,
    CONSTRAINT UX_Users_Email UNIQUE (Email)
);

IF OBJECT_ID('auth.Courses') IS NULL
CREATE TABLE auth.Courses (
    Id        INT NOT NULL PRIMARY KEY,          -- id del curso en Moodle
    ShortName NVARCHAR(100) NOT NULL,
    FullName  NVARCHAR(300) NOT NULL
);

IF OBJECT_ID('auth.TeacherCourses') IS NULL
CREATE TABLE auth.TeacherCourses (
    UserId   INT NOT NULL,
    CourseId INT NOT NULL,
    PRIMARY KEY (UserId, CourseId),
    FOREIGN KEY (UserId)   REFERENCES auth.Users(Id),
    FOREIGN KEY (CourseId) REFERENCES auth.Courses(Id)
);
GO
