namespace AuthCourses.Api;

// ---------- Entidades (esquema auth) ----------

public class AppUser
{
    public int Id { get; set; }
    public string Email { get; set; } = "";
    public string Name { get; set; } = "";
    public string Role { get; set; } = "teacher"; // teacher | admin
    public string PasswordHash { get; set; } = "";
}

public class CourseEntity
{
    public int Id { get; set; } // id del curso en Moodle
    public string ShortName { get; set; } = "";
    public string FullName { get; set; } = "";
}

public class TeacherCourse
{
    public int UserId { get; set; }
    public int CourseId { get; set; }
}

// ---------- Cuerpos de petición y respuesta (según auth-courses.v1.yaml) ----------

public record LoginRequest(string Email, string Password);
public record UserDto(int Id, string Name, string? Email, string Role);
public record LoginResponse(string AccessToken, string TokenType, int ExpiresIn, UserDto User);
public record CourseDto(int Id, string ShortName, string FullName, int? StudentCount, DateTimeOffset? LastSyncAt);
public record ProblemDto(string Title, int Status, string Code, string? Detail, string TraceId);
