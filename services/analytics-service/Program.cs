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
app.MapGet("/api/v1/courses/{courseId:int}/analytics/alerts", async (int courseId, int? studentId, string? severity, string? status, int? page, int? pageSize, AnalyticsDbContext db, CancellationToken ct) =>
{
    var currentPage = page is null or < 1 ? 1 : page.Value;
    var currentPageSize = pageSize is null or < 1 or > 200 ? 50 : pageSize.Value;
    var data = await LoadCourse(courseId, db, ct);
    if (data is null) return Results.NotFound(new Problem("Curso no encontrado", 404, "COURSE_NOT_FOUND", "No existen observaciones para el curso."));
    var rules = await LoadRules(db, ct);
    var items = BuildAlerts(courseId, data.Value.grades, data.Value.completions, rules)
        .Where(x => !studentId.HasValue || x.StudentId == studentId.Value)
        .Where(x => string.IsNullOrWhiteSpace(severity) || x.Severity.Equals(severity, StringComparison.OrdinalIgnoreCase))
        .Where(x => string.IsNullOrWhiteSpace(status) || x.Status.Equals(status, StringComparison.OrdinalIgnoreCase))
        .ToArray();
    return Results.Ok(new AlertPage(items.Skip((currentPage - 1) * currentPageSize).Take(currentPageSize).ToArray(), currentPage, currentPageSize, items.Length));
});
app.MapGet("/api/v1/courses/{courseId:int}/analytics/report", async (int courseId, AnalyticsDbContext db, CancellationToken ct) =>
{
    var data = await LoadCourse(courseId, db, ct);
    if (data is null) return Results.NotFound(new Problem("Curso no encontrado", 404, "COURSE_NOT_FOUND", "No existen observaciones para el curso."));
    var response = ToCourse(courseId, data.Value.grades, data.Value.completions);
    var rules = await LoadRules(db, ct);
    var alerts = BuildAlerts(courseId, data.Value.grades, data.Value.completions, rules);
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
static async Task<Dictionary<string, AlertRuleRow>> LoadRules(AnalyticsDbContext db, CancellationToken ct) => await db.AlertRules.AsNoTracking().Where(x => x.Enabled).ToDictionaryAsync(x => x.RuleCode, StringComparer.OrdinalIgnoreCase, ct);
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
static List<AlertResponse> BuildAlerts(int courseId, List<GradeRow> grades, List<CompletionRow> completions, IReadOnlyDictionary<string, AlertRuleRow> rules)
{
    var output = new List<AlertResponse>();
    foreach (var sid in grades.Select(x => x.StudentId).Concat(completions.Select(x => x.StudentId)).Distinct())
    {
        var sg = grades.Where(x => x.StudentId == sid).ToList();
        var sc = completions.Where(x => x.StudentId == sid).ToList();
        var indicators = AnalyticsCalculator.Calculate(sg.Select(ToGrade), sc.Select(ToCompletion));
        var sourceIds = sg.Select(x => x.ActivityId.ToString()).Concat(sc.Select(x => x.ActivityId.ToString())).Distinct().ToArray();
        AddThresholdAlert(output, rules, courseId, sid, "LOW_AVERAGE", "averageScore10", indicators.AverageScore10.Value, indicators.Counts.GradedCount >= 2, sourceIds, "El promedio normalizado está por debajo del umbral configurado.");
        AddThresholdAlert(output, rules, courseId, sid, "LOW_SUBMISSION", "submissionRate", indicators.SubmissionRate.Value, sg.Count > 0, sourceIds, "La tasa de entregas enviadas está por debajo del umbral configurado.");
        AddThresholdAlert(output, rules, courseId, sid, "PENDING_GRADING", "pendingGradingRate", indicators.PendingGradingRate.Value, indicators.Counts.PendingGradingCount > 0, sourceIds, "La tasa de actividades pendientes supera el umbral configurado.");
        AddThresholdAlert(output, rules, courseId, sid, "LOW_COMPLETION", "completionRate", indicators.CompletionRate.Value, indicators.CompletionRate.Value.HasValue, sourceIds, "La tasa de finalización está por debajo del umbral configurado.");
        if (indicators.CompletionRate.Status == "unavailable" && rules.TryGetValue("NO_DATA", out var noData) && noData.Enabled)
            output.Add(Alert(courseId, sid, noData, "completionRate", null, null, sourceIds, "Moodle no entregó observaciones de seguimiento de finalización."));
    }
    return output;
}
static void AddThresholdAlert(List<AlertResponse> output, IReadOnlyDictionary<string, AlertRuleRow> rules, int courseId, int studentId, string ruleCode, string metric, decimal? value, bool precondition, string[] sourceIds, string explanation)
{
    if (!precondition || value is not decimal observed || !rules.TryGetValue(ruleCode, out var rule) || rule.Threshold is not decimal threshold || !Compare(observed, rule.Operator, threshold)) return;
    output.Add(Alert(courseId, studentId, rule, metric, observed, threshold, sourceIds, explanation));
}
static bool Compare(decimal value, string op, decimal threshold) => op.Trim().ToLowerInvariant() switch { "lt" or "<" => value < threshold, "lte" or "<=" => value <= threshold, "gt" or ">" => value > threshold, "gte" or ">=" => value >= threshold, "eq" or "=" => value == threshold, _ => false };
static CourseAnalyticsResponse ToCourse(int id, List<GradeRow> grades, List<CompletionRow> completions) { var c = AnalyticsCalculator.Calculate(grades.Select(ToGrade), completions.Select(ToCompletion)); return new(id, Meta(grades, completions), c.AverageScore10, c.SubmissionRate, c.GradingRate, c.CompletionRate, c.PendingGradingRate, c.Counts); }
static StudentAnalyticsResponse ToStudent(int course, int student, List<GradeRow> grades, List<CompletionRow> completions) { var c = AnalyticsCalculator.Calculate(grades.Select(ToGrade), completions.Select(ToCompletion)); return new(course, student, Meta(grades, completions), c.AverageScore10, c.SubmissionRate, c.GradingRate, c.CompletionRate, c.PendingGradingRate, c.Counts); }
static SnapshotMeta Meta(List<GradeRow> grades, List<CompletionRow> completions) => new(grades.FirstOrDefault()?.SyncId ?? completions.FirstOrDefault()?.SyncId ?? "unknown", grades.FirstOrDefault()?.SyncId ?? completions.FirstOrDefault()?.SyncId, DateTime.UtcNow, grades.Count == 0 && completions.Count == 0 ? "unavailable" : completions.Count == 0 || completions.Any(x => Normalize(x.State).Equals("NotAvailable", StringComparison.OrdinalIgnoreCase)) ? "partial" : "complete");
static GradeObservation ToGrade(GradeRow x) => new() { CourseId=x.CourseId, StudentId=x.StudentId, ActivityId=x.ActivityId, Status=Enum.Parse<GradeStatus>(Normalize(x.Status), true), SubmissionStatus=Enum.Parse<SubmissionStatus>(Normalize(x.SubmissionStatus), true), Score=x.Score, MaxScore=x.MaxScore };
static CompletionObservation ToCompletion(CompletionRow x) => new() { CourseId=x.CourseId, StudentId=x.StudentId, ActivityId=x.ActivityId, State=Enum.Parse<CompletionState>(Normalize(x.State), true) };
static string Normalize(string value) => value.Replace("_", "");
static AlertResponse Alert(int course, int? student, AlertRuleRow rule, string metric, decimal? value, decimal? threshold, string[] sourceIds, string explanation) => new($"{rule.RuleCode}-{course}-{student}", rule.RuleCode, course, student, rule.Severity, "active", DateTime.UtcNow, null, new[] { new AlertEvidence(metric, value, threshold, null, null, sourceIds, explanation) });
