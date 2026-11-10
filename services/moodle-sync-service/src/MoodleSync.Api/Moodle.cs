using System.Text.Json;

namespace MoodleSync.Api;

internal static class J
{
    public static int? Int(JsonElement e, string n)
    {
        if (e.ValueKind == JsonValueKind.Object && e.TryGetProperty(n, out var v)
            && v.ValueKind == JsonValueKind.Number && v.TryGetInt32(out var i)) return i;
        return null;
    }

    public static long? Long(JsonElement e, string n)
    {
        if (e.ValueKind == JsonValueKind.Object && e.TryGetProperty(n, out var v)
            && v.ValueKind == JsonValueKind.Number && v.TryGetInt64(out var l)) return l;
        return null;
    }

    public static double? Num(JsonElement e, string n)
    {
        if (e.ValueKind == JsonValueKind.Object && e.TryGetProperty(n, out var v)
            && v.ValueKind == JsonValueKind.Number && v.TryGetDouble(out var d)) return d;
        return null;
    }

    public static string? Str(JsonElement e, string n)
    {
        if (e.ValueKind == JsonValueKind.Object && e.TryGetProperty(n, out var v)
            && v.ValueKind == JsonValueKind.String) return v.GetString();
        return null;
    }

    public static DateTimeOffset? Ts(long? t)
    {
        if (t is null || t <= 0) return null;
        return DateTimeOffset.FromUnixTimeSeconds(t.Value);
    }
}

// Cliente de solo lectura de los servicios web de Moodle.
// El token viaja en el cuerpo de un POST, nunca en la URL, y no se escribe en los registros.
public sealed class MoodleClient(IHttpClientFactory factory, IConfiguration config)
{
    public async Task<JsonElement> CallAsync(string function, CancellationToken ct, params (string Key, string Value)[] ps)
    {
        var token = config["MOODLE_WS_TOKEN"];
        if (string.IsNullOrWhiteSpace(token))
            throw new MoodleApiException("missing_token", "Falta MOODLE_WS_TOKEN en la configuración del servicio.");

        var form = new List<KeyValuePair<string, string>>
        {
            new("wstoken", token),
            new("wsfunction", function),
            new("moodlewsrestformat", "json"),
        };
        foreach (var (k, v) in ps) form.Add(new(k, v));

        string text;
        try
        {
            using var response = await factory.CreateClient("moodle")
                .PostAsync("/webservice/rest/server.php", new FormUrlEncodedContent(form), ct);
            if (!response.IsSuccessStatusCode)
                throw new MoodleUnavailableException($"Moodle respondió con HTTP {(int)response.StatusCode}.");
            text = await response.Content.ReadAsStringAsync(ct);
        }
        catch (HttpRequestException ex)
        {
            throw new MoodleUnavailableException("No se pudo conectar con Moodle.", ex);
        }
        catch (TaskCanceledException ex) when (!ct.IsCancellationRequested)
        {
            throw new MoodleUnavailableException("Moodle tardó demasiado en responder.", ex);
        }

        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(text);
        }
        catch (JsonException ex)
        {
            throw new MoodleUnavailableException("Moodle devolvió una respuesta que no es JSON.", ex);
        }

        using (doc)
        {
            var root = doc.RootElement.Clone();
            if (root.ValueKind == JsonValueKind.Object && root.TryGetProperty("exception", out _))
                throw new MoodleApiException(J.Str(root, "errorcode") ?? "unknown", J.Str(root, "message") ?? "Error de Moodle.");
            return root;
        }
    }
}

public sealed record AssignmentInfo(int Id, int Cmid, string Name, double MaxScore);
public sealed record GradeInfo(double? Score, double? Max, DateTimeOffset? GradedAt);
public sealed record SubmissionInfo(string? Status, DateTimeOffset? ModifiedAt);
public sealed record CompletionInfo(int State, int Tracking);

// Traduce lo que devuelve Moodle al formato del contrato.
// Solo se leen metadatos: nunca se toca el texto de las entregas (plugins / onlinetext).
public static class Normalizer
{
    public static List<StudentDto> ParseStudents(JsonElement enrolled)
    {
        var list = new List<StudentDto>();
        if (enrolled.ValueKind != JsonValueKind.Array) return list;
        foreach (var u in enrolled.EnumerateArray())
        {
            var isStudent = u.TryGetProperty("roles", out var roles) && roles.ValueKind == JsonValueKind.Array
                && roles.EnumerateArray().Any(r => J.Str(r, "shortname") == "student");
            if (isStudent && J.Int(u, "id") is int id)
                list.Add(new StudentDto(id, J.Str(u, "fullname") ?? "", J.Str(u, "email")));
        }
        return list.OrderBy(s => s.Id).ToList();
    }

    public static List<AssignmentInfo> ParseAssignments(JsonElement r)
    {
        var list = new List<AssignmentInfo>();
        if (!r.TryGetProperty("courses", out var courses) || courses.ValueKind != JsonValueKind.Array) return list;
        foreach (var c in courses.EnumerateArray())
        {
            if (!c.TryGetProperty("assignments", out var assignments) || assignments.ValueKind != JsonValueKind.Array) continue;
            foreach (var a in assignments.EnumerateArray())
                if (J.Int(a, "id") is int id && J.Int(a, "cmid") is int cmid)
                    list.Add(new AssignmentInfo(id, cmid, J.Str(a, "name") ?? "", J.Num(a, "grade") ?? 0));
        }
        return list;
    }

    public static Dictionary<(int User, int Cmid), GradeInfo> ParseGrades(JsonElement r)
    {
        var map = new Dictionary<(int, int), GradeInfo>();
        if (!r.TryGetProperty("usergrades", out var usergrades) || usergrades.ValueKind != JsonValueKind.Array) return map;
        foreach (var ug in usergrades.EnumerateArray())
        {
            if (J.Int(ug, "userid") is not int uid) continue;
            if (!ug.TryGetProperty("gradeitems", out var items) || items.ValueKind != JsonValueKind.Array) continue;
            foreach (var gi in items.EnumerateArray())
                if (J.Str(gi, "itemmodule") == "assign" && J.Int(gi, "cmid") is int cmid)
                    map[(uid, cmid)] = new GradeInfo(J.Num(gi, "graderaw"), J.Num(gi, "grademax"), J.Ts(J.Long(gi, "gradedategraded")));
        }
        return map;
    }

    public static Dictionary<(int AssignId, int User), SubmissionInfo> ParseSubmissions(JsonElement r)
    {
        var map = new Dictionary<(int, int), SubmissionInfo>();
        if (!r.TryGetProperty("assignments", out var assignments) || assignments.ValueKind != JsonValueKind.Array) return map;
        foreach (var a in assignments.EnumerateArray())
        {
            if (J.Int(a, "assignmentid") is not int aid) continue;
            if (!a.TryGetProperty("submissions", out var subs) || subs.ValueKind != JsonValueKind.Array) continue;
            foreach (var s in subs.EnumerateArray())
                if (J.Int(s, "userid") is int uid)
                    map[(aid, uid)] = new SubmissionInfo(J.Str(s, "status"), J.Ts(J.Long(s, "timemodified")));
        }
        return map;
    }

    public static Dictionary<int, CompletionInfo> ParseCompletion(JsonElement r)
    {
        var map = new Dictionary<int, CompletionInfo>();
        if (!r.TryGetProperty("statuses", out var statuses) || statuses.ValueKind != JsonValueKind.Array) return map;
        foreach (var s in statuses.EnumerateArray())
            if (J.Int(s, "cmid") is int cmid)
                map[cmid] = new CompletionInfo(J.Int(s, "state") ?? -1, J.Int(s, "tracking") ?? 0);
        return map;
    }

    public static (List<GradeEntryDto> Grades, List<ActivityProgressDto> Progress) Build(
        StudentDto student,
        IReadOnlyList<AssignmentInfo> assignments,
        IReadOnlyDictionary<(int User, int Cmid), GradeInfo> grades,
        IReadOnlyDictionary<(int AssignId, int User), SubmissionInfo> submissions,
        IReadOnlyDictionary<int, CompletionInfo> completion,
        List<string> warnings)
    {
        var gradeList = new List<GradeEntryDto>();
        var progressList = new List<ActivityProgressDto>();

        foreach (var a in assignments)
        {
            var hasGrade = grades.TryGetValue((student.Id, a.Cmid), out var g);
            double? score = hasGrade ? g!.Score : null;
            double max = (hasGrade ? g!.Max : null) ?? a.MaxScore;
            var gradedAt = hasGrade ? g!.GradedAt : null;

            var hasSub = submissions.TryGetValue((a.Id, student.Id), out var sub);
            var raw = hasSub ? sub!.Status : null;
            var submission = raw switch
            {
                "submitted" => "submitted",
                "draft" => "draft",
                _ => "none",
            };
            if (hasSub && raw is not ("submitted" or "draft" or "new"))
                warnings.Add($"Estudiante {student.Id}, actividad {a.Cmid}: estado de entrega desconocido '{raw}' (se trata como none).");

            var submittedAt = submission == "submitted" && hasSub ? sub!.ModifiedAt : null;

            // Una nota nula nunca es 0. Con nota: graded. Entregó y sin nota: pending_grading. Si no: not_submitted.
            var status = score != null ? "graded"
                       : submission == "submitted" ? "pending_grading"
                       : "not_submitted";

            gradeList.Add(new GradeEntryDto(student.Id, a.Cmid, a.Name, status, submission, score, max, submittedAt, gradedAt));

            // Sin seguimiento de finalización configurado, o sin dato: not_available (nunca null ni 0).
            var state = "not_available";
            if (completion.TryGetValue(a.Cmid, out var c) && c.Tracking != 0)
                state = c.State switch
                {
                    0 => "incomplete",
                    1 => "complete",
                    2 => "passed",
                    3 => "failed",
                    _ => "not_available",
                };
            progressList.Add(new ActivityProgressDto(a.Cmid, "assign", state));
        }

        return (gradeList, progressList);
    }
}
