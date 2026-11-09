using Microsoft.EntityFrameworkCore;

namespace EduMonitor.Analytics;

public sealed class AnalyticsDbContext(DbContextOptions<AnalyticsDbContext> options) : DbContext(options)
{
    public DbSet<CourseRow> Courses => Set<CourseRow>();
    public DbSet<GradeRow> Grades => Set<GradeRow>();
    public DbSet<CompletionRow> Completions => Set<CompletionRow>();
    public DbSet<AlertRuleRow> AlertRules => Set<AlertRuleRow>();
    protected override void OnModelCreating(ModelBuilder b)
    {
        b.Entity<CourseRow>().ToTable("course", "sync").HasKey(x => x.CourseId);
        b.Entity<CourseRow>().Property(x => x.CourseId).HasColumnName("course_id");
        b.Entity<CourseRow>().Property(x => x.ShortName).HasColumnName("short_name");
        b.Entity<CourseRow>().Property(x => x.FullName).HasColumnName("full_name");
        b.Entity<CourseRow>().Property(x => x.LastSyncAt).HasColumnName("last_sync_at");

        b.Entity<GradeRow>().ToTable("grade", "sync").HasKey(x => x.GradeId);
        b.Entity<GradeRow>().Property(x => x.GradeId).HasColumnName("grade_id");
        b.Entity<GradeRow>().Property(x => x.CourseId).HasColumnName("course_id");
        b.Entity<GradeRow>().Property(x => x.StudentId).HasColumnName("student_id");
        b.Entity<GradeRow>().Property(x => x.ActivityId).HasColumnName("activity_id");
        b.Entity<GradeRow>().Property(x => x.SubmissionStatus).HasColumnName("submission_status");
        b.Entity<GradeRow>().Property(x => x.MaxScore).HasColumnName("max_score");
        b.Entity<GradeRow>().Property(x => x.SyncId).HasColumnName("sync_id");
        b.Entity<GradeRow>().Property(x => x.SyncedAt).HasColumnName("synced_at");

        b.Entity<CompletionRow>().ToTable("completion", "sync").HasKey(x => x.CompletionId);
        b.Entity<CompletionRow>().Property(x => x.CompletionId).HasColumnName("completion_id");
        b.Entity<CompletionRow>().Property(x => x.CourseId).HasColumnName("course_id");
        b.Entity<CompletionRow>().Property(x => x.StudentId).HasColumnName("student_id");
        b.Entity<CompletionRow>().Property(x => x.ActivityId).HasColumnName("activity_id");
        b.Entity<CompletionRow>().Property(x => x.SyncId).HasColumnName("sync_id");
        b.Entity<CompletionRow>().Property(x => x.ObservedAt).HasColumnName("observed_at");

        b.Entity<AlertRuleRow>().ToTable("alert_rule", "analytics").HasKey(x => x.RuleCode);
        b.Entity<AlertRuleRow>().Property(x => x.RuleCode).HasColumnName("rule_code");
        b.Entity<AlertRuleRow>().Property(x => x.Threshold).HasColumnName("threshold");
        b.Entity<AlertRuleRow>().Property(x => x.Operator).HasColumnName("operator");
        b.Entity<AlertRuleRow>().Property(x => x.Enabled).HasColumnName("enabled");
        b.Entity<AlertRuleRow>().Property(x => x.Severity).HasColumnName("severity");
    }
}
public sealed class CourseRow { public int CourseId { get; set; } public string ShortName { get; set; } = ""; public string FullName { get; set; } = ""; public DateTime? LastSyncAt { get; set; } }
public sealed class GradeRow { public int GradeId { get; set; } public int CourseId { get; set; } public int StudentId { get; set; } public int ActivityId { get; set; } public string Status { get; set; } = ""; public string SubmissionStatus { get; set; } = ""; public decimal? Score { get; set; } public decimal MaxScore { get; set; } public string SyncId { get; set; } = ""; public DateTime SyncedAt { get; set; } }
public sealed class CompletionRow { public int CompletionId { get; set; } public int CourseId { get; set; } public int StudentId { get; set; } public int ActivityId { get; set; } public string State { get; set; } = ""; public string SyncId { get; set; } = ""; public DateTime ObservedAt { get; set; } }
public sealed class AlertRuleRow { public string RuleCode { get; set; } = ""; public string Name { get; set; } = ""; public string Metric { get; set; } = ""; public string Operator { get; set; } = ""; public decimal? Threshold { get; set; } public string Severity { get; set; } = "info"; public bool Enabled { get; set; } }
