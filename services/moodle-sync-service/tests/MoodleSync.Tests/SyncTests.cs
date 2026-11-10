using System.Globalization;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Xunit;

namespace MoodleSync.Tests;

public class SyncTests
{
    private static string Line(JsonElement g)
    {
        var score = g.GetProperty("score").ValueKind == JsonValueKind.Null
            ? "-"
            : g.GetProperty("score").GetDouble().ToString(CultureInfo.InvariantCulture);
        return $"{g.GetProperty("studentId").GetInt32()}|{g.GetProperty("activityId").GetInt32()}|{g.GetProperty("status").GetString()}|{g.GetProperty("submissionStatus").GetString()}|{score}";
    }

    private static async Task AssertProblem(HttpResponseMessage r, HttpStatusCode status, string code)
    {
        Assert.Equal(status, r.StatusCode);
        Assert.Equal("application/problem+json", r.Content.Headers.ContentType?.MediaType);
        var body = await r.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal(code, body.GetProperty("code").GetString());
    }

    [Fact]
    public async Task Antes_de_sincronizar_las_lecturas_devuelven_503_DATA_NOT_AVAILABLE()
    {
        using var env = new TestEnv();
        await AssertProblem(await env.Http.GetAsync("/courses/2/students"), HttpStatusCode.ServiceUnavailable, "DATA_NOT_AVAILABLE");
        await AssertProblem(await env.Http.GetAsync("/courses/2/grades"), HttpStatusCode.ServiceUnavailable, "DATA_NOT_AVAILABLE");
    }

    [Fact]
    public async Task El_estado_de_un_curso_sin_sincronizar_es_never()
    {
        using var env = new TestEnv();
        var status = await env.JsonAsync("/courses/2/sync");
        Assert.Equal("never", status.GetProperty("state").GetString());
    }

    [Fact]
    public async Task Sin_token_devuelve_401()
    {
        using var env = new TestEnv();
        var r = await env.Anonymous().GetAsync("/courses/2/students");
        await AssertProblem(r, HttpStatusCode.Unauthorized, "TOKEN_INVALID");
    }

    [Fact]
    public async Task Sincronizar_guarda_estudiantes_y_notas_con_su_estado()
    {
        using var env = new TestEnv();
        var status = await env.SyncAndWaitAsync(2);
        Assert.Equal("succeeded", status.GetProperty("state").GetString());
        Assert.NotEqual(JsonValueKind.Null, status.GetProperty("lastSuccessAt").ValueKind);

        var students = await env.JsonAsync("/courses/2/students");
        Assert.Equal(5, students.GetProperty("total").GetInt32());

        var grades = await env.JsonAsync("/courses/2/grades?pageSize=200");
        var actual = grades.GetProperty("items").EnumerateArray().Select(Line).OrderBy(x => x).ToArray();
        var expected = new[]
        {
            "4|2|graded|submitted|8",          "4|3|not_submitted|draft|-",
            "5|2|graded|submitted|0",          "5|3|graded|submitted|90",
            "6|2|pending_grading|submitted|-", "6|3|not_submitted|none|-",
            "7|2|not_submitted|none|-",        "7|3|not_submitted|none|-",
            "8|2|graded|submitted|5",          "8|3|not_submitted|none|-",
        }.OrderBy(x => x).ToArray();
        Assert.Equal(expected, actual);
    }

    [Fact]
    public async Task El_token_de_Moodle_va_en_el_cuerpo_y_no_en_la_URL()
    {
        using var env = new TestEnv();
        await env.SyncAndWaitAsync(2);
        Assert.True(env.Moodle.Queries.Count > 5);
        Assert.All(env.Moodle.Queries, q => Assert.Equal("", q));
        Assert.Equal(0, env.Moodle.RequestsWithoutToken);
    }

    [Fact]
    public async Task El_texto_de_las_entregas_no_aparece_y_solo_salen_los_campos_permitidos()
    {
        using var env = new TestEnv();
        await env.SyncAndWaitAsync(2);

        var texto = new StringBuilder();
        foreach (var url in new[] { "/courses/2/grades?pageSize=200", "/courses/2/students", "/courses/2/students/4", "/courses/2/sync" })
            texto.Append(await (await env.Http.GetAsync(url)).Content.ReadAsStringAsync());
        Assert.DoesNotContain(FakeMoodle.SecretoDeLaEntrega, texto.ToString());
        Assert.DoesNotContain("onlinetext", texto.ToString(), StringComparison.OrdinalIgnoreCase);

        // Lista de campos permitidos de una calificación (no depende de buscar una palabra).
        var grades = await env.JsonAsync("/courses/2/grades?pageSize=1");
        var campos = grades.GetProperty("items")[0].EnumerateObject().Select(p => p.Name).OrderBy(x => x).ToArray();
        var permitidos = new[] { "studentId", "activityId", "activityName", "status", "submissionStatus", "score", "maxScore", "submittedAt", "gradedAt" }
            .OrderBy(x => x).ToArray();
        Assert.Equal(permitidos, campos);
    }

    [Fact]
    public async Task La_ficha_del_estudiante_incluye_notas_y_progreso()
    {
        using var env = new TestEnv();
        await env.SyncAndWaitAsync(2);

        var ficha = await env.JsonAsync("/courses/2/students/4");
        Assert.Equal(2, ficha.GetProperty("grades").GetArrayLength());
        var progreso = ficha.GetProperty("activities").EnumerateArray()
            .ToDictionary(a => a.GetProperty("activityId").GetInt32(), a => a.GetProperty("completionState").GetString());
        Assert.Equal("complete", progreso[2]);
        Assert.Equal("incomplete", progreso[3]);
    }

    [Fact]
    public async Task Estudiante_inexistente_devuelve_404()
    {
        using var env = new TestEnv();
        await env.SyncAndWaitAsync(2);
        await AssertProblem(await env.Http.GetAsync("/courses/2/students/99"), HttpStatusCode.NotFound, "STUDENT_NOT_FOUND");
    }

    [Fact]
    public async Task La_paginacion_respeta_pageSize_y_total()
    {
        using var env = new TestEnv();
        await env.SyncAndWaitAsync(2);

        var p1 = await env.JsonAsync("/courses/2/students?page=1&pageSize=2");
        Assert.Equal(2, p1.GetProperty("items").GetArrayLength());
        Assert.Equal(5, p1.GetProperty("total").GetInt32());

        var p3 = await env.JsonAsync("/courses/2/students?page=3&pageSize=2");
        Assert.Equal(1, p3.GetProperty("items").GetArrayLength());
    }

    [Fact]
    public async Task Una_segunda_sincronizacion_simultanea_devuelve_409()
    {
        using var env = new TestEnv();
        env.Moodle.Delay = TimeSpan.FromSeconds(1);
        var primera = await env.Http.PostAsync("/courses/2/sync", null);
        Assert.Equal(HttpStatusCode.Accepted, primera.StatusCode);

        var segunda = await env.Http.PostAsync("/courses/2/sync", null);
        await AssertProblem(segunda, HttpStatusCode.Conflict, "SYNC_IN_PROGRESS");
    }

    [Fact]
    public async Task Si_Moodle_no_responde_al_iniciar_devuelve_503()
    {
        using var env = new TestEnv(moodleUrlOverride: "http://127.0.0.1:1");
        var r = await env.Http.PostAsync("/courses/2/sync", null);
        await AssertProblem(r, HttpStatusCode.ServiceUnavailable, "MOODLE_UNAVAILABLE");
    }

    [Fact]
    public async Task Un_error_de_Moodle_deja_la_sincronizacion_en_failed_sin_datos_engañosos()
    {
        using var env = new TestEnv();
        env.Moodle.Failing.Add("core_enrol_get_enrolled_users");
        var status = await env.SyncAndWaitAsync(2);
        Assert.Equal("failed", status.GetProperty("state").GetString());
        Assert.Equal("MOODLE_ERROR", status.GetProperty("errorCode").GetString());

        // No se guardó nada a medias: sigue sin datos.
        await AssertProblem(await env.Http.GetAsync("/courses/2/students"), HttpStatusCode.ServiceUnavailable, "DATA_NOT_AVAILABLE");
    }

    [Fact]
    public async Task Un_curso_que_Moodle_no_conoce_termina_en_failed()
    {
        using var env = new TestEnv();
        var status = await env.SyncAndWaitAsync(77);
        Assert.Equal("failed", status.GetProperty("state").GetString());
        Assert.Equal("COURSE_NOT_IN_MOODLE", status.GetProperty("errorCode").GetString());
    }
}
