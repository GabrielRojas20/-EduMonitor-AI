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
    var data = await LoadCourse(courseId, db, ct);
    return data is null ? Results.NotFound(new Problem("Curso no encontrado", 404, "COURSE_NOT_FOUND", "No existen observaciones para el curso.")) : Results.Ok(ToCourse(courseId, data.Value.grades, data.Value.completions));
});
app.MapGet("/api/v1/courses/{courseId:int}/analytics/summary", async (int courseId, AnalyticsDbContext db, CancellationToken ct) => await Summary(courseId, db, ct));
app.MapGet("/api/v1/courses/{courseId:int}/analytics/students/{studentId:int}", async (int courseId, int studentId, AnalyticsDbContext db, CancellationToken ct) => await Student(courseId, studentId, db, ct));
app.MapGet("/api/v1/courses/{courseId:int}/students/{studentId:int}/analytics", async (int courseId, int studentId, AnalyticsDbContext db, CancellationToken ct) => await Student(courseId, studentId, db, ct));
app.MapGet("/api/v1/courses/{courseId:int}/analytics/alerts", async (int courseId, int? studentId, string? severity, string? status, int page, int pageSize, AnalyticsDbContext db, CancellationToken ct) =>
{
    page = page < 1 ? 1 : page;
    pageSize = pageSize is < 1 or > 200 ? 50 : pageSize;
    var grades = await db.Grades.AsNoTracking().Where(x => x.CourseId == courseId).ToListAsync(ct);
    var completions = await db.Completions.AsNoTracking().Where(x => x.CourseId == courseId).ToListAsync(ct);
    var students = grades.Select(x => x.StudentId).Concat(completions.Select(x => x.StudentId)).Distinct();
    var items = new List<AlertResponse>();
    foreach (var sid in students)
    {
        if (studentId.HasValue && sid != studentId.Value) continue;
        var sg = grades.Where(x => x.StudentId == sid).ToList();
        var sc = completions.Where(x => x.StudentId == sid).ToList();
        var indicators = AnalyticsCalculator.Calculate(sg.Select(ToGrade), sc.Select(ToCompletion));
        var sourceIds = sg.Select(x => x.ActivityId.ToString()).Concat(sc.Select(x => x.ActivityId.ToString())).Distinct().ToArray();
        if (indicators.AverageScore10.Value is decimal avg && indicators.Counts.GradedCount >= 2 && avg < 6) items.Add(Alert(courseId, sid, "LOW_AVERAGE", "warning", "averageScore10", avg, 6, sourceIds, "El promedio normalizado está por debajo de 6/10."));
        if (indicators.SubmissionRate.Value is decimal submission && sg.Count > 0 && submission < 80) items.Add(Alert(courseId, sid, "LOW_SUBMISSION", "warning", "submissionRate", submission, 80, sourceIds, "La tasa de entregas enviadas está por debajo de 80%."));
        if (indicators.PendingGradingRate.Value is decimal pending && indicators.Counts.PendingGradingCount > 0 && pending > 20) items.Add(Alert(courseId, sid, "PENDING_GRADING", "info", "pendingGradingRate", pending, 20, sourceIds, "La tasa de actividades pendientes de calificación supera 20%."));
        if (indicators.CompletionRate.Value is decimal completion && completion < 70) items.Add(Alert(courseId, sid, "LOW_COMPLETION", "warning", "completionRate", completion, 70, sourceIds, "La tasa de finalización está por debajo de 70%."));
        if (indicators.CompletionRate.Status == "unavailable") items.Add(Alert(courseId, sid, "NO_DATA", "info", "completionRate", null, null, sourceIds, "Moodle no entregó observaciones de seguimiento de finalización."));
    }
    var filtered = items.Where(x => string.IsNullOrWhiteSpace(severity) || x.Severity.Equals(severity, StringComparison.OrdinalIgnoreCase)).Where(x => string.IsNullOrWhiteSpace(status) || x.Status.Equals(status, StringComparison.OrdinalIgnoreCase)).ToArray();
    return Results.Ok(new AlertPage(filtered.Skip((page - 1) * pageSize).Take(pageSize).ToArray(), page, pageSize, filtered.Length));
});
app.MapGet("/api/v1/courses/{courseId:int}/analytics/report", async (int courseId, AnalyticsDbContext db, CancellationToken ct) =>
{
    var data = await LoadCourse(courseId, db, ct);
    if (data is null) return Results.NotFound(new Problem("Curso no encontrado", 404, "COURSE_NOT_FOUND", "No existen observaciones para el curso."));
    var response = ToCourse(courseId, data.Value.grades, data.Value.completions);
    var alerts = await BuildAlerts(courseId, data.Value.grades, data.Value.completions);
    var findings = alerts.SelectMany(a => a.Evidence.Select(e => new ReportFinding(a.AlertId, a.RuleCode, a.StudentId, e.Metric, e.Explanation))).ToArray();
    return Results.Ok(new CourseReportData(courseId, response.Snapshot, null, null, new Dictionary<string, Metric> { ["averageScore10"] = response.AverageScore10, ["submissionRate"] = response.SubmissionRate, ["gradingRate"] = response.GradingRate, ["completionRate"] = response.CompletionRate, ["pendingGradingRate"] = response.PendingGradingRate }, findings, alerts.Count(a => a.Status == "active")));
});
app.Run();

static async Task<(List<GradeRow> grades, List<CompletionRow> completions)?> LoadCourse(int courseId, AnalyticsDbContext db, CancellationToken ct)
{
    var grades = await db.Grades.AsNoTracking().Where(x => x.CourseId == courseId).ToListAsync(ct);
    var completions = await db.Completions.AsNoTracking().Where(x => x.CourseId == courseId).ToListAsync(ct);
    return grades.Count == 0 && completions.Count == 0 ? null : (grades, completions);
}
static async Task<IResult> Summary(int courseId, AnalyticsDbContext db, CancellationToken ct)
{
    var data = await LoadCourse(courseId, db, ct);
    return data is null ? Results.NotFound() : Results.Ok(ToCourse(courseId, data.Value.grades, data.Value.completions));
}
static async Task<IResult> Student(int courseId, int studentId, AnalyticsDbContext db, CancellationToken ct)
{
    var grades = await db.Grades.AsNoTracking().Where(x => x.CourseId == courseId && x.StudentId == studentId).ToListAsync(ct);
    var completions = await db.Completions.AsNoTracking().Where(x => x.CourseId == courseId && x.StudentId == studentId).ToListAsync(ct);
    return grades.Count == 0 && completions.Count == 0 ? Results.NotFound(new Problem("Estudiante no encontrado", 404, "STUDENT_NOT_FOUND", "No existen observaciones para el estudiante en el curso.")) : Results.Ok(ToStudent(courseId, studentId, grades, completions));
}
static async Task<List<AlertResponse>> BuildAlerts(int courseId, List<GradeRow> grades, List<CompletionRow> completions)
{
    var output = new List<AlertResponse>();
    foreach (var sid in grades.Select(x => x.StudentId).Concat(completions.Select(x => x.StudentId)).Distinct())
    {
        var sg = grades.Where(x => x.StudentId == sid).ToList();
        var sc = completions.Where(x => x.StudentId == sid).ToList();
        var i = AnalyticsCalculator.Calculate(sg.Select(ToGrade), sc.Select(ToCompletion));
        var ids = sg.Select(x => x.ActivityId.ToString()).Concat(sc.Select(x => x.ActivityId.ToString())).Distinct().ToArray();
        if (i.AverageScore10.Value is decimal avg && i.Counts.GradedCount >= 2 && avg < 6) output.Add(Alert(courseId, sid, "LOW_AVERAGE", "warning", "averageScore10", avg, 6, ids, "El promedio normalizado está por debajo de 6/10."));
        if (i.SubmissionRate.Value is decimal sub && sg.Count > 0 && sub < 80) output.Add(Alert(courseId, sid, "LOW_SUBMISSION", "warning", "submissionRate", sub, 80, ids, "La tasa de entregas enviadas está por debajo de 80%."));
        if (i.PendingGradingRate.Value is decimal pending && i.Counts.PendingGradingCount > 0 && pending > 20) output.Add(Alert(courseId, sid, "PENDING_GRADING", "info", "pendingGradingRate", pending, 20, ids, "La tasa de actividades pendientes de calificación supera 20%."));
        if (i.CompletionRate.Value is decimal comp && comp < 70) output.Add(Alert(courseId, sid, "LOW_COMPLETION", "warning", "completionRate", comp, 70, ids, "La tasa de finalización está por debajo de 70%."));
        if (i.CompletionRate.Status == "unavailable") output.Add(Alert(courseId, sid, "NO_DATA", "info", "completionRate", null, null, ids, "Moodle no entregó observaciones de seguimiento de finalización."));
    }
    return output;
}
static CourseAnalyticsResponse ToCourse(int id, List<GradeRow> grades, List<CompletionRow> completions) { var c = AnalyticsCalculator.Calculate(grades.Select(ToGrade), completions.Select(ToCompletion)); return new(id, Meta(grades, completions), c.AverageScore10, c.SubmissionRate, c.GradingRate, c.CompletionRate, c.PendingGradingRate, c.Counts); }
static StudentAnalyticsResponse ToStudent(int course, int student, List<GradeRow> grades, List<CompletionRow> completions) { var c = AnalyticsCalculator.Calculate(grades.Select(ToGrade), completions.Select(ToCompletion)); return new(course, student, Meta(grades, completions), c.AverageScore10, c.SubmissionRate, c.GradingRate, c.CompletionRate, c.PendingGradingRate, c.Counts); }
static SnapshotMeta Meta(List<GradeRow> grades, List<CompletionRow> completions) => new(grades.FirstOrDefault()?.SyncId ?? completions.FirstOrDefault()?.SyncId ?? "unknown", grades.FirstOrDefault()?.SyncId ?? completions.FirstOrDefault()?.SyncId, DateTime.UtcNow, grades.Count == 0 && completions.Count == 0 ? "unavailable" : completions.Count == 0 || completions.Any(x => Normalize(x.State).Equals("NotAvailable", StringComparison.OrdinalIgnoreCase)) ? "partial" : "complete");
static GradeObservation ToGrade(GradeRow x) => new() { CourseId=x.CourseId, StudentId=x.StudentId, ActivityId=x.ActivityId, Status=Enum.Parse<GradeStatus>(Normalize(x.Status), true), SubmissionStatus=Enum.Parse<SubmissionStatus>(Normalize(x.SubmissionStatus), true), Score=x.Score, MaxScore=x.MaxScore };
static CompletionObservation ToCompletion(CompletionRow x) => new() { CourseId=x.CourseId, StudentId=x.StudentId, ActivityId=x.ActivityId, State=Enum.Parse<CompletionState>(Normalize(x.State), true) };
static string Normalize(string value) => value.Replace("_", "");
static AlertResponse Alert(int course, int? student, string rule, string severity, string metric, decimal? value, decimal? threshold, string[] sourceIds, string explanation) => new($"{rule}-{course}-{student}", rule, course, student, severity, "active", DateTime.UtcNow, null, new[] { new AlertEvidence(metric, value, threshold, null, null, sourceIds, explanation) });
