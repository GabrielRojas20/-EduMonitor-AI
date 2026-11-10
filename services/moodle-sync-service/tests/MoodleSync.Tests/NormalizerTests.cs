using System.Text.Json;
using MoodleSync.Api;
using Xunit;

namespace MoodleSync.Tests;

public class NormalizerTests
{
    private static readonly StudentDto Est = new(4, "Estudiante Uno", null);
    private static readonly AssignmentInfo[] Tarea = { new(1, 2, "Tarea 1", 10) };

    private static GradeEntryDto Un(
        GradeInfo? nota, SubmissionInfo? entrega, CompletionInfo? finalizacion, out ActivityProgressDto progreso, List<string>? avisos = null)
    {
        var notas = new Dictionary<(int, int), GradeInfo>();
        if (nota is not null) notas[(4, 2)] = nota;
        var entregas = new Dictionary<(int, int), SubmissionInfo>();
        if (entrega is not null) entregas[(1, 4)] = entrega;
        var comp = new Dictionary<int, CompletionInfo>();
        if (finalizacion is not null) comp[2] = finalizacion;
        var (g, p) = Normalizer.Build(Est, Tarea, notas, entregas, comp, avisos ?? new List<string>());
        progreso = p.Single();
        return g.Single();
    }

    [Fact]
    public void Nota_cero_es_graded_con_puntaje_0()
    {
        var g = Un(new GradeInfo(0, 10, null), new SubmissionInfo("submitted", null), null, out _);
        Assert.Equal("graded", g.Status);
        Assert.Equal(0.0, g.Score);
    }

    [Fact]
    public void Entregado_sin_nota_es_pending_grading_y_el_puntaje_es_nulo()
    {
        var g = Un(new GradeInfo(null, 10, null), new SubmissionInfo("submitted", null), null, out _);
        Assert.Equal("pending_grading", g.Status);
        Assert.Null(g.Score);
    }

    [Fact]
    public void Borrador_es_not_submitted_con_submissionStatus_draft()
    {
        var g = Un(new GradeInfo(null, 10, null), new SubmissionInfo("draft", null), null, out _);
        Assert.Equal("not_submitted", g.Status);
        Assert.Equal("draft", g.SubmissionStatus);
    }

    [Fact]
    public void Sin_entrega_es_not_submitted_con_submissionStatus_none()
    {
        var g = Un(new GradeInfo(null, 10, null), null, null, out _);
        Assert.Equal("not_submitted", g.Status);
        Assert.Equal("none", g.SubmissionStatus);
    }

    [Fact]
    public void Sin_ningun_dato_de_nota_usa_el_maximo_de_la_tarea_y_no_inventa_ceros()
    {
        var g = Un(null, null, null, out _);
        Assert.Null(g.Score);
        Assert.Equal(10, g.MaxScore);
    }

    [Fact]
    public void Sin_finalizacion_configurada_es_not_available()
    {
        Un(null, null, null, out var sinDato);
        Assert.Equal("not_available", sinDato.CompletionState);

        Un(null, null, new CompletionInfo(1, 0), out var sinSeguimiento);
        Assert.Equal("not_available", sinSeguimiento.CompletionState);
    }

    [Theory]
    [InlineData(0, "incomplete")]
    [InlineData(1, "complete")]
    [InlineData(2, "passed")]
    [InlineData(3, "failed")]
    [InlineData(9, "not_available")]
    public void Estados_de_finalizacion_de_Moodle(int estado, string esperado)
    {
        Un(null, null, new CompletionInfo(estado, 2), out var p);
        Assert.Equal(esperado, p.CompletionState);
    }

    [Fact]
    public void Un_estado_de_entrega_desconocido_se_trata_como_none_y_avisa()
    {
        var avisos = new List<string>();
        var g = Un(null, new SubmissionInfo("reopened", null), null, out _, avisos);
        Assert.Equal("none", g.SubmissionStatus);
        Assert.Single(avisos);
    }

    [Fact]
    public void Las_entregas_nuevas_no_generan_aviso()
    {
        var avisos = new List<string>();
        Un(null, new SubmissionInfo("new", null), null, out _, avisos);
        Assert.Empty(avisos);
    }

    [Fact]
    public void Solo_se_toman_los_usuarios_con_rol_student()
    {
        var json = """
        [
          {"id":3,"fullname":"Docente","roles":[{"shortname":"editingteacher"}]},
          {"id":4,"fullname":"Estudiante Uno","email":"e1@example.com","roles":[{"shortname":"student"}]},
          {"id":5,"fullname":"Sin roles"}
        ]
        """;
        var estudiantes = Normalizer.ParseStudents(JsonDocument.Parse(json).RootElement);
        Assert.Equal(new[] { 4 }, estudiantes.Select(s => s.Id).ToArray());
    }
}
