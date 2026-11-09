namespace EduMonitor.Analytics;

public sealed record SnapshotMeta(string SnapshotId, string? SyncId, DateTime CalculatedAt, string DataQuality);
public sealed record CourseAnalyticsResponse(int CourseId, SnapshotMeta Snapshot, Metric AverageScore10, Metric SubmissionRate, Metric GradingRate, Metric CompletionRate, Metric PendingGradingRate, Counts Counts);
public sealed record StudentAnalyticsResponse(int CourseId, int StudentId, SnapshotMeta Snapshot, Metric AverageScore10, Metric SubmissionRate, Metric GradingRate, Metric CompletionRate, Metric PendingGradingRate, Counts Counts);
public sealed record AlertEvidence(string Metric, decimal? ObservedValue, decimal? Threshold, int? Numerator, int? Denominator, string[] SourceIds, string Explanation);
public sealed record AlertResponse(string AlertId, string RuleCode, int CourseId, int? StudentId, string Severity, string Status, DateTime DetectedAt, DateTime? ResolvedAt, AlertEvidence[] Evidence);
public sealed record AlertPage(AlertResponse[] Items, int Page, int PageSize, int Total);
public sealed record ReportFinding(string? AlertId, string? RuleCode, int? StudentId, string? Metric, string Text);
public sealed record CourseReportData(int CourseId, SnapshotMeta Snapshot, DateTime? PeriodStart, DateTime? PeriodEnd, Dictionary<string, Metric> Metrics, ReportFinding[] Findings, int ActiveAlertCount);
public sealed record Problem(string Title, int Status, string Code, string Detail, string? TraceId = null);
