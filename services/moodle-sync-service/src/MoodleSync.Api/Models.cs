using System.Text.Json.Serialization;

namespace MoodleSync.Api;

// ---------- Datos que devuelve el servicio (según moodle-sync.v1.yaml) ----------

public record StudentDto(int Id, string FullName, string? Email);

public record GradeEntryDto(int StudentId, int ActivityId, string ActivityName, string Status, string SubmissionStatus,
    double? Score, double MaxScore, DateTimeOffset? SubmittedAt, DateTimeOffset? GradedAt);

public record ActivityProgressDto(int ActivityId, string ActivityType, string CompletionState);

public record StudentDetailDto(StudentDto Student, IReadOnlyList<GradeEntryDto> Grades, IReadOnlyList<ActivityProgressDto> Activities);

public record SyncStatusDto(string State, DateTimeOffset? StartedAt, DateTimeOffset? FinishedAt, DateTimeOffset? LastSuccessAt,
    string? ErrorCode, string? Message);

public record SyncAcceptedDto(string SyncId, string State);

public record PageDto<T>(IReadOnlyList<T> Items, int Page, int PageSize, int Total);

public record ProblemDto(string Title, int Status, string Code,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Detail, string TraceId);

// Lo sincronizado de un curso. Nunca contiene el texto de las entregas.
public record CourseSnapshot(int CourseId, string ShortName, string FullName, DateTimeOffset SyncedAt,
    IReadOnlyList<StudentDto> Students, IReadOnlyList<GradeEntryDto> Grades,
    IReadOnlyDictionary<int, IReadOnlyList<ActivityProgressDto>> Progress);

// ---------- Errores de Moodle ----------

// Moodle no responde: no hay conexión, tardó demasiado, HTTP con error o respuesta que no es JSON.
public sealed class MoodleUnavailableException(string message, Exception? inner = null) : Exception(message, inner);

// Moodle respondió con un error propio (token inválido, permiso denegado, función no disponible...).
public sealed class MoodleApiException(string errorCode, string message) : Exception(message)
{
    public string ErrorCode { get; } = errorCode;
}

public sealed class CourseNotFoundInMoodleException(int courseId)
    : Exception($"El curso {courseId} no está disponible para el usuario del servicio web.");
