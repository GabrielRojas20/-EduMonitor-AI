using EduMonitor.Analytics;
using Xunit;

namespace EduMonitor.Analytics.Tests;

public class AnalyticsCalculatorTests
{
    [Fact]
    public void NotaCeroEsCalificadaYNoSeConvierteEnAusencia()
    {
        var result = AnalyticsCalculator.Calculate(new[] { Grade(GradeStatus.Graded, SubmissionStatus.Submitted, 0, 10) }, Array.Empty<CompletionObservation>());
        Assert.Equal(1, result.Counts.GradedCount);
        Assert.Equal(0m, result.AverageScore10.Value);
        Assert.Equal("available", result.AverageScore10.Status);
    }

    [Fact]
    public void PendienteYNoEntregadoNoEntranAlPromedio()
    {
        var result = AnalyticsCalculator.Calculate(new[]
        {
            Grade(GradeStatus.Graded, SubmissionStatus.Submitted, 8, 10),
            Grade(GradeStatus.PendingGrading, SubmissionStatus.Submitted, null, 10),
            Grade(GradeStatus.NotSubmitted, SubmissionStatus.Draft, null, 10)
        }, Array.Empty<CompletionObservation>());
        Assert.Equal(8m, result.AverageScore10.Value);
        Assert.Equal(1, result.Counts.PendingGradingCount);
        Assert.Equal(1, result.Counts.NotSubmittedCount);
        Assert.Equal(1, result.Counts.DraftCount);
    }

    [Fact]
    public void CalculaPromedioNormalizadoSobreDiez()
    {
        var result = AnalyticsCalculator.Calculate(new[]
        {
            Grade(GradeStatus.Graded, SubmissionStatus.Submitted, 8, 10),
            Grade(GradeStatus.Graded, SubmissionStatus.Submitted, 90, 100)
        }, Array.Empty<CompletionObservation>());
        Assert.Equal(8.5m, result.AverageScore10.Value);
        Assert.Equal("score_0_10", result.AverageScore10.Unit);
    }

    [Fact]
    public void CalculaTasaDeEntrega()
    {
        var result = AnalyticsCalculator.Calculate(new[]
        {
            Grade(GradeStatus.Graded, SubmissionStatus.Submitted, 8, 10),
            Grade(GradeStatus.NotSubmitted, SubmissionStatus.Draft, null, 10),
            Grade(GradeStatus.PendingGrading, SubmissionStatus.Submitted, null, 10),
            Grade(GradeStatus.NotSubmitted, SubmissionStatus.None, null, 10)
        }, Array.Empty<CompletionObservation>());
        Assert.Equal(50m, result.SubmissionRate.Value);
        Assert.Equal(2, result.SubmissionRate.Numerator);
        Assert.Equal(4, result.SubmissionRate.Denominator);
    }

    [Fact]
    public void CalculaTasaDeCalificacionSobreEvaluadasYPendientes()
    {
        var result = AnalyticsCalculator.Calculate(new[]
        {
            Grade(GradeStatus.Graded, SubmissionStatus.Submitted, 8, 10),
            Grade(GradeStatus.PendingGrading, SubmissionStatus.Submitted, null, 10),
            Grade(GradeStatus.NotSubmitted, SubmissionStatus.Draft, null, 10)
        }, Array.Empty<CompletionObservation>());
        Assert.Equal(50m, result.GradingRate.Value);
        Assert.Equal(1, result.GradingRate.Numerator);
        Assert.Equal(2, result.GradingRate.Denominator);
    }

    [Fact]
    public void CalculaTasaDeFinalizacionYMarcaDatosParciales()
    {
        var result = AnalyticsCalculator.Calculate(Array.Empty<GradeObservation>(), new[]
        {
            Completion(CompletionState.Complete),
            Completion(CompletionState.NotAvailable),
            Completion(CompletionState.Incomplete)
        });
        Assert.Equal(50m, result.CompletionRate.Value);
        Assert.Equal("partial", result.CompletionRate.Status);
        Assert.Equal(1, result.CompletionRate.Numerator);
        Assert.Equal(2, result.CompletionRate.Denominator);
    }

    [Fact]
    public void CalculaTasaDePendientesDeCalificar()
    {
        var result = AnalyticsCalculator.Calculate(new[]
        {
            Grade(GradeStatus.PendingGrading, SubmissionStatus.Submitted, null, 10),
            Grade(GradeStatus.Graded, SubmissionStatus.Submitted, 8, 10),
            Grade(GradeStatus.NotSubmitted, SubmissionStatus.None, null, 10),
            Grade(GradeStatus.PendingGrading, SubmissionStatus.Submitted, null, 10)
        }, Array.Empty<CompletionObservation>());
        Assert.Equal(50m, result.PendingGradingRate.Value);
        Assert.Equal(2, result.PendingGradingRate.Numerator);
        Assert.Equal(4, result.PendingGradingRate.Denominator);
    }

    [Fact]
    public void SinDatosDevuelveNoDisponibleSinConvertirAceros()
    {
        var result = AnalyticsCalculator.Calculate(Array.Empty<GradeObservation>(), new[] { Completion(CompletionState.NotAvailable) });
        Assert.Null(result.AverageScore10.Value);
        Assert.Equal("DATA_NOT_AVAILABLE", result.AverageScore10.Code);
        Assert.Null(result.SubmissionRate.Value);
        Assert.Null(result.GradingRate.Value);
        Assert.Null(result.CompletionRate.Value);
        Assert.Equal("unavailable", result.CompletionRate.Status);
        Assert.Null(result.PendingGradingRate.Value);
    }

    [Theory]
    [InlineData("lt", 5, 6, true)]
    [InlineData("lt", 6, 6, false)]
    [InlineData("lte", 6, 6, true)]
    [InlineData("gt", 7, 6, true)]
    [InlineData("gt", 6, 6, false)]
    [InlineData("gte", 6, 6, true)]
    [InlineData("eq", 6, 6, true)]
    [InlineData("eq", 6, 7, false)]
    public void LasReglasRespetanOperadorYLimite(string op, int value, int threshold, bool expected)
    {
        Assert.Equal(expected, AlertRuleEvaluator.Matches(value, op, threshold));
    }

    [Fact]
    public void ElPeriodoDelInformeUsaLaPrimeraYUltimaObservacion()
    {
        var first = new DateTime(2026, 11, 1, 10, 0, 0, DateTimeKind.Utc);
        var last = new DateTime(2026, 11, 3, 10, 0, 0, DateTimeKind.Utc);

        var period = ReportPeriod.From(new[] { last, first, first.AddHours(2) });

        Assert.Equal(first, period.Start);
        Assert.Equal(last, period.End);
    }

    [Fact]
    public void ElPeriodoDelInformeEsNuloSinObservaciones()
    {
        var period = ReportPeriod.From(Array.Empty<DateTime>());

        Assert.Null(period.Start);
        Assert.Null(period.End);
    }

    private static GradeObservation Grade(GradeStatus status, SubmissionStatus submission, decimal? score, decimal maxScore) => new()
    {
        Status = status,
        SubmissionStatus = submission,
        Score = score,
        MaxScore = maxScore
    };

    private static CompletionObservation Completion(CompletionState state) => new() { State = state };
}
