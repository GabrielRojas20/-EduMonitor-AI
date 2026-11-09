using Microsoft.EntityFrameworkCore;

namespace EduMonitor.Analytics;

public sealed class AnalyticsDbContext(DbContextOptions<AnalyticsDbContext> options) : DbContext(options)
{
    public DbSet<CourseRow> Courses => Set<CourseRow>();
    public DbSet<GradeRow> Grades => Set<GradeRow>();
    public DbSet<CompletionRow> Completions => Set<CompletionRow>();
    protected override void OnModelCreating(ModelBuilder b)
    {
        b.Entity<CourseRow>().ToTable("course", "sync").HasKey(x => x.CourseId);
        b.Entity<GradeRow>().ToTable("grade", "sync").HasKey(x => x.GradeId);
        b.Entity<CompletionRow>().ToTable("completion", "sync").HasKey(x => x.CompletionId);
    }
}
public sealed class CourseRow { public int CourseId { get; set; } public string ShortName { get; set; } = ""; public string FullName { get; set; } = ""; public DateTime? LastSyncAt { get; set; } }
public sealed class GradeRow { public int GradeId { get; set; } public int CourseId { get; set; } public int StudentId { get; set; } public int ActivityId { get; set; } public string Status { get; set; } = ""; public string SubmissionStatus { get; set; } = ""; public decimal? Score { get; set; } public decimal MaxScore { get; set; } public string SyncId { get; set; } = ""; public DateTime SyncedAt { get; set; } }
public sealed class CompletionRow { public int CompletionId { get; set; } public int CourseId { get; set; } public int StudentId { get; set; } public int ActivityId { get; set; } public string State { get; set; } = ""; public string SyncId { get; set; } = ""; public DateTime ObservedAt { get; set; } }
