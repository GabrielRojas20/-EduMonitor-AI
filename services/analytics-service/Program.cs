using EduMonitor.Analytics;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);
var connection = Environment.GetEnvironmentVariable("ConnectionStrings__EduMonitor")
    ?? builder.Configuration.GetConnectionString("EduMonitor")
    ?? "Server=localhost,1433;Database=EduMonitor;User Id=sa;Password=YourStrong!Passw0rd;TrustServerCertificate=True;";
builder.Services.AddDbContext<AnalyticsDbContext>(o => o.UseSqlServer(connection));
builder.Services.AddHealthChecks();
builder.Services.AddProblemDetails();
var app = builder.Build();
app.UseExceptionHandler();
app.MapHealthChecks("/health");

app.MapGet("/api/v1/courses/{courseId:int}/analytics", async (int courseId, AnalyticsDbContext db, CancellationToken ct) =>
{
    var grades = await db.Grades.AsNoTracking().Where(x => x.CourseId == courseId).ToListAsync(ct);
    var completions = await db.Completions.AsNoTracking().Where(x => x.CourseId == courseId).ToListAsync(ct);
    if (grades.Count == 0 && completions.Count == 0) return Results.NotFound(new Problem("Curso no encontrado", 404, "COURSE_NOT_FOUND", "No existen observaciones para el curso."));
    return Results.Ok(ToCourse(courseId, grades, completions));
});
app.MapGet("/api/v1/courses/{courseId:int}/analytics/summary", async (int courseId, AnalyticsDbContext db, CancellationToken ct) =>
    await Summary(courseId, db, ct));
app.MapGet("/api/v1/courses/{courseId:int}/analytics/students/{studentId:int}", async (int courseId, int studentId, AnalyticsDbContext db, CancellationToken ct) =>
    await Student(courseId, studentId, db, ct));
app.MapGet("/api/v1/courses/{courseId:int}/students/{studentId:int}/analytics", async (int courseId, int studentId, AnalyticsDbContext db, CancellationToken ct) =>
    await Student(courseId, studentId, db, ct));
app.MapGet("/api/v1/courses/{courseId:int}/analytics/alerts", async (int courseId, AnalyticsDbContext db, CancellationToken ct) =>
{
    var all = await db.Grades.AsNoTracking().Where(x => x.CourseId == courseId).ToListAsync(ct);
    var byStudent = all.GroupBy(x => x.StudentId);
    var items = new List<AlertResponse>();
    foreach (var group in byStudent)
    {
        var indicators = AnalyticsCalculator.Calculate(group.Select(ToGrade), Array.Empty<CompletionObservation>());
        if (indicators.AverageScore10.Value is decimal avg && avg < 6) items.Add(Alert(courseId, group.Key, "LOW_AVERAGE", "warning", "averageScore10", avg, 6, "El promedio normalizado está por debajo de 6/10."));
        if (indicators.SubmissionRate.Value is decimal submission && submission < 60) items.Add(Alert(courseId, group.Key, "LOW_SUBMISSION", "warning", "submissionRate", submission, 60, "La tasa de entregas enviadas está por debajo de 60%."));
        if (indicators.PendingGradingRate.Value is decimal pending && pending > 30) items.Add(Alert(courseId, group.Key, "PENDING_GRADING", "critical", "pendingGradingRate", pending, 30, "Hay demasiadas actividades enviadas pendientes de calificación."));
    }
    return Results.Ok(new AlertPage(items.ToArray(), 1, items.Count, items.Count));
});

app.Run();

static async Task<IResult> Summary(int courseId, AnalyticsDbContext db, CancellationToken ct)
{
    var grades = await db.Grades.AsNoTracking().Where(x => x.CourseId == courseId).ToListAsync(ct);
    var completions = await db.Completions.AsNoTracking().Where(x => x.CourseId == courseId).ToListAsync(ct);
    return grades.Count == 0 && completions.Count == 0 ? Results.NotFound() : Results.Ok(ToCourse(courseId, grades, completions));
}
static async Task<IResult> Student(int courseId, int studentId, AnalyticsDbContext db, CancellationToken ct)
{
    var grades = await db.Grades.AsNoTracking().Where(x => x.CourseId == courseId && x.StudentId == studentId).ToListAsync(ct);
    var completions = await db.Completions.AsNoTracking().Where(x => x.CourseId == courseId && x.StudentId == studentId).ToListAsync(ct);
    return grades.Count == 0 && completions.Count == 0 ? Results.NotFound() : Results.Ok(ToStudent(courseId, studentId, grades, completions));
}
static CourseAnalyticsResponse ToCourse(int id, List<GradeRow> grades, List<CompletionRow> completions)
{
    var c = AnalyticsCalculator.Calculate(grades.Select(ToGrade), completions.Select(ToCompletion));
    return new(id, Meta(grades), c.AverageScore10, c.SubmissionRate, c.GradingRate, c.CompletionRate, c.PendingGradingRate, c.Counts);
}
static StudentAnalyticsResponse ToStudent(int course, int student, List<GradeRow> grades, List<CompletionRow> completions)
{
    var c = AnalyticsCalculator.Calculate(grades.Select(ToGrade), completions.Select(ToCompletion));
    return new(course, student, Meta(grades), c.AverageScore10, c.SubmissionRate, c.GradingRate, c.CompletionRate, c.PendingGradingRate, c.Counts);
}
static SnapshotMeta Meta(List<GradeRow> grades) => new(grades.FirstOrDefault()?.SyncId ?? "unknown", grades.FirstOrDefault()?.SyncId, DateTime.UtcNow, grades.Count == 0 ? "not_available" : "complete");
static GradeObservation ToGrade(GradeRow x) => new() { CourseId=x.CourseId, StudentId=x.StudentId, ActivityId=x.ActivityId, Status=Enum.Parse<GradeStatus>(Normalize(x.Status), true), SubmissionStatus=Enum.Parse<SubmissionStatus>(Normalize(x.SubmissionStatus), true), Score=x.Score, MaxScore=x.MaxScore };
static CompletionObservation ToCompletion(CompletionRow x) => new() { CourseId=x.CourseId, StudentId=x.StudentId, ActivityId=x.ActivityId, State=Enum.Parse<CompletionState>(Normalize(x.State), true) };
static string Normalize(string value) => value.Replace("_", "");
static AlertResponse Alert(int course, int? student, string rule, string severity, string metric, decimal value, decimal threshold, string explanation) => new($"{rule}-{course}-{student}", rule, course, student, severity, "active", DateTime.UtcNow, null, new[] { new AlertEvidence(metric, value, threshold, null, null, Array.Empty<string>(), explanation) });
