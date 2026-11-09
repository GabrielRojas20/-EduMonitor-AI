namespace EduMonitor.Analytics;

public enum GradeStatus { Graded, PendingGrading, NotSubmitted }
public enum SubmissionStatus { None, Draft, Submitted }
public enum CompletionState { Complete, Incomplete, Passed, Failed, NotAvailable }

public sealed class GradeObservation
{
    public int CourseId { get; init; }
    public int StudentId { get; init; }
    public int ActivityId { get; init; }
    public GradeStatus Status { get; init; }
    public SubmissionStatus SubmissionStatus { get; init; }
    public decimal? Score { get; init; }
    public decimal MaxScore { get; init; }
}

public sealed class CompletionObservation
{
    public int CourseId { get; init; }
    public int StudentId { get; init; }
    public int ActivityId { get; init; }
    public CompletionState State { get; init; }
}

public sealed record Metric(decimal? Value, string Unit, string Status, string? Code = null, int? Numerator = null, int? Denominator = null, string? Detail = null);
public sealed record Counts(int GradedCount, int PendingGradingCount, int NotSubmittedCount, int DraftCount);
public sealed record CalculatedIndicators(Metric AverageScore10, Metric SubmissionRate, Metric GradingRate, Metric CompletionRate, Metric PendingGradingRate, Counts Counts);

public static class AnalyticsCalculator
{
    public static CalculatedIndicators Calculate(IEnumerable<GradeObservation> grades, IEnumerable<CompletionObservation> completions)
    {
        var gs = grades.ToList();
        var cs = completions.ToList();
        var graded = gs.Count(x => x.Status == GradeStatus.Graded && x.Score.HasValue && x.MaxScore > 0);
        var pending = gs.Count(x => x.Status == GradeStatus.PendingGrading);
        var notSubmitted = gs.Count(x => x.Status == GradeStatus.NotSubmitted);
        var drafts = gs.Count(x => x.SubmissionStatus == SubmissionStatus.Draft);
        var submitted = gs.Count(x => x.SubmissionStatus == SubmissionStatus.Submitted);
        var average = graded == 0 ? Unavailable("No hay calificaciones evaluadas") : Available(gs.Where(x => x.Status == GradeStatus.Graded && x.Score.HasValue && x.MaxScore > 0).Average(x => x.Score!.Value / x.MaxScore * 10m), "score_0_10");
        var submission = Rate(submitted, gs.Count, "percent");
        var grading = Rate(graded, graded + pending, "percent");
        var availableCompletion = cs.Where(x => x.State != CompletionState.NotAvailable).ToList();
        var completed = availableCompletion.Count(x => x.State is CompletionState.Complete or CompletionState.Passed);
        var completion = Rate(completed, availableCompletion.Count, "percent");
        if (availableCompletion.Count > 0 && availableCompletion.Count < cs.Count)
            completion = completion with { Status = "partial", Detail = "Algunas actividades no tienen seguimiento de finalización disponible." };
        var pendingRate = Rate(pending, gs.Count, "percent");
        return new(average, submission, grading, completion, pendingRate, new(graded, pending, notSubmitted, drafts));
    }

    private static Metric Available(decimal value, string unit) => new(Math.Round(value, 2), unit, "available");
    private static Metric Rate(int numerator, int denominator, string unit) => denominator == 0 ? Unavailable("No hay datos suficientes", unit) : new(Math.Round(100m * numerator / denominator, 2), unit, "available", null, numerator, denominator);
    private static Metric Unavailable(string detail, string unit = "percent") => new(null, unit, "unavailable", "DATA_NOT_AVAILABLE", null, null, detail);
}
