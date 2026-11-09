using EduMonitor.Analytics;
using Xunit;

namespace EduMonitor.Analytics.Tests;

public class AnalyticsCalculatorTests
{
    [Fact]
    public void NotaCeroEsCalificadaYNoSeConvierteEnAusencia()
    {
        var result = AnalyticsCalculator.Calculate(new[] { new GradeObservation { Status = GradeStatus.Graded, SubmissionStatus = SubmissionStatus.Submitted, Score = 0, MaxScore = 10 } }, Array.Empty<CompletionObservation>());
        Assert.Equal(1, result.Counts.GradedCount);
        Assert.Equal(0m, result.AverageScore10.Value);
        Assert.Equal("available", result.AverageScore10.Status);
    }

    [Fact]
    public void PendienteYNoEntregadoNoEntranAlPromedio()
    {
        var result = AnalyticsCalculator.Calculate(new[] {
            new GradeObservation { Status = GradeStatus.Graded, SubmissionStatus = SubmissionStatus.Submitted, Score = 8, MaxScore = 10 },
            new GradeObservation { Status = GradeStatus.PendingGrading, SubmissionStatus = SubmissionStatus.Submitted, Score = null, MaxScore = 10 },
            new GradeObservation { Status = GradeStatus.NotSubmitted, SubmissionStatus = SubmissionStatus.Draft, Score = null, MaxScore = 10 }
        }, Array.Empty<CompletionObservation>());
        Assert.Equal(8m, result.AverageScore10.Value);
        Assert.Equal(1, result.Counts.PendingGradingCount);
        Assert.Equal(1, result.Counts.NotSubmittedCount);
        Assert.Equal(1, result.Counts.DraftCount);
    }

    [Fact]
    public void SinDatosDevuelveNoDisponible()
    {
        var result = AnalyticsCalculator.Calculate(Array.Empty<GradeObservation>(), new[] { new CompletionObservation { State = CompletionState.NotAvailable } });
        Assert.Null(result.AverageScore10.Value);
        Assert.Equal("DATA_NOT_AVAILABLE", result.AverageScore10.Code);
        Assert.Equal("unavailable", result.CompletionRate.Status);
    }
}
