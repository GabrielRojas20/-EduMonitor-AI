using System.Diagnostics;
using System.Text.Json;

// Prototipo LOCAL del cliente de Moodle (Sprint 2). No subir al repositorio hasta que empiece el Sprint 2.
// Lee Moodle de solo lectura y convierte los datos al formato de moodle-sync.v1.yaml:
// status de la calificación, submissionStatus y completionState. Nunca lee ni guarda el texto de las entregas.

var baseUrl = Environment.GetEnvironmentVariable("MOODLE_URL") ?? "http://localhost:8080";
var tokenFile = Environment.GetEnvironmentVariable("MOODLE_TOKEN_FILE") ?? @"C:\edumonitor-moodle\token.txt";
string token = Environment.GetEnvironmentVariable("MOODLE_TOKEN") ?? File.ReadAllText(tokenFile).Trim();

using var http = new HttpClient { BaseAddress = new Uri(baseUrl), Timeout = TimeSpan.FromSeconds(60) };
var jsonOptions = new JsonSerializerOptions(JsonSerializerDefaults.Web) { WriteIndented = true };

// ---------- Ayudas para leer JSON ----------
int? Int(JsonElement e, string n)
{
    if (e.ValueKind == JsonValueKind.Object && e.TryGetProperty(n, out var v)
        && v.ValueKind == JsonValueKind.Number && v.TryGetInt32(out var i)) return i;
    return null;
}

long? Long(JsonElement e, string n)
{
    if (e.ValueKind == JsonValueKind.Object && e.TryGetProperty(n, out var v)
        && v.ValueKind == JsonValueKind.Number && v.TryGetInt64(out var l)) return l;
    return null;
}

double? Num(JsonElement e, string n)
{
    if (e.ValueKind == JsonValueKind.Object && e.TryGetProperty(n, out var v)
        && v.ValueKind == JsonValueKind.Number && v.TryGetDouble(out var d)) return d;
    return null;
}

string? Str(JsonElement e, string n)
{
    if (e.ValueKind == JsonValueKind.Object && e.TryGetProperty(n, out var v)
        && v.ValueKind == JsonValueKind.String) return v.GetString();
    return null;
}

DateTimeOffset? Ts(long? t)
{
    if (t is null || t <= 0) return null;
    return DateTimeOffset.FromUnixTimeSeconds(t.Value);
}

// ---------- Llamada a Moodle (POST: el token no queda en la URL) ----------
async Task<JsonElement> Call(string fn, params (string k, string v)[] ps)
{
    var form = new List<KeyValuePair<string, string>>
    {
        new("wstoken", token),
        new("wsfunction", fn),
        new("moodlewsrestformat", "json"),
    };
    foreach (var (k, v) in ps) form.Add(new(k, v));

    using var resp = await http.PostAsync("/webservice/rest/server.php", new FormUrlEncodedContent(form));
    var text = await resp.Content.ReadAsStringAsync();
    resp.EnsureSuccessStatusCode();

    using var doc = JsonDocument.Parse(text);
    var root = doc.RootElement.Clone();
    if (root.ValueKind == JsonValueKind.Object && root.TryGetProperty("exception", out _))
        throw new Exception($"{fn}: {Str(root, "errorcode")} - {Str(root, "message")}");
    return root;
}

// ---------- Sincronización de un curso ----------
async Task SyncCourse(int cid, string shortName, string fullName)
{
    var warnings = new List<string>();

    // Estudiantes (rol student). El username no llega al rol docente; se usa el id de Moodle.
    var enrolled = await Call("core_enrol_get_enrolled_users", ("courseid", cid.ToString()));
    var students = new List<StudentOut>();
    foreach (var u in enrolled.EnumerateArray())
    {
        var isStudent = u.TryGetProperty("roles", out var roles) && roles.ValueKind == JsonValueKind.Array
            && roles.EnumerateArray().Any(r => Str(r, "shortname") == "student");
        if (isStudent)
            students.Add(new(u.GetProperty("id").GetInt32(), Str(u, "fullname") ?? "", Str(u, "email")));
    }

    // Tareas del curso: id de la tarea (assignmentid) y cmid (el activityId del contrato)
    var asg = await Call("mod_assign_get_assignments", ("courseids[0]", cid.ToString()));
    var assigns = new List<(int Id, int Cmid, string Name, double Max)>();
    foreach (var co in asg.GetProperty("courses").EnumerateArray())
        foreach (var a in co.GetProperty("assignments").EnumerateArray())
            assigns.Add((a.GetProperty("id").GetInt32(), a.GetProperty("cmid").GetInt32(),
                         Str(a, "name") ?? "", Num(a, "grade") ?? 0));

    // Notas por (estudiante, cmid)
    var grades = await Call("gradereport_user_get_grade_items", ("courseid", cid.ToString()));
    var gradeByKey = new Dictionary<(int User, int Cmid), JsonElement>();
    foreach (var ug in grades.GetProperty("usergrades").EnumerateArray())
    {
        var uid = ug.GetProperty("userid").GetInt32();
        foreach (var gi in ug.GetProperty("gradeitems").EnumerateArray())
            if (Str(gi, "itemmodule") == "assign" && Int(gi, "cmid") is int cm)
                gradeByKey[(uid, cm)] = gi;
    }

    // Estado de las entregas por (tarea, estudiante). Solo se leen metadatos, nunca el texto.
    var subs = new Dictionary<(int AssignId, int User), JsonElement>();
    if (assigns.Count > 0)
    {
        var ps = assigns.Select((a, i) => ($"assignmentids[{i}]", a.Id.ToString())).ToArray();
        var sres = await Call("mod_assign_get_submissions", ps);
        foreach (var a in sres.GetProperty("assignments").EnumerateArray())
        {
            var aid = a.GetProperty("assignmentid").GetInt32();
            foreach (var s in a.GetProperty("submissions").EnumerateArray())
                subs[(aid, s.GetProperty("userid").GetInt32())] = s;
        }
    }

    // Armar el detalle de cada estudiante: calificaciones y progreso
    var details = new List<StudentDetailOut>();
    foreach (var st in students)
    {
        // Progreso: Moodle solo acepta un userid por llamada
        var comp = await Call("core_completion_get_activities_completion_status",
            ("courseid", cid.ToString()), ("userid", st.Id.ToString()));
        var byCmid = new Dictionary<int, (int State, int Tracking)>();
        foreach (var s in comp.GetProperty("statuses").EnumerateArray())
            if (Int(s, "cmid") is int cm)
                byCmid[cm] = (Int(s, "state") ?? -1, Int(s, "tracking") ?? 0);

        var gradeList = new List<GradeOut>();
        var progList = new List<ProgressOut>();
        foreach (var a in assigns)
        {
            var hasGrade = gradeByKey.TryGetValue((st.Id, a.Cmid), out var gi);
            double? score = hasGrade ? Num(gi, "graderaw") : null;
            double max = (hasGrade ? Num(gi, "grademax") : null) ?? a.Max;
            var gradedAt = hasGrade ? Ts(Long(gi, "gradedategraded")) : null;

            var hasSub = subs.TryGetValue((a.Id, st.Id), out var sub);
            var rawStatus = hasSub ? Str(sub, "status") : null;
            var submission = rawStatus switch
            {
                "submitted" => "submitted",
                "draft" => "draft",
                _ => "none",
            };
            if (hasSub && rawStatus is not ("submitted" or "draft" or "new"))
                warnings.Add($"estudiante {st.Id}, {a.Name}: estado de entrega desconocido '{rawStatus}' (se trata como none)");

            var submittedAt = submission == "submitted" && hasSub ? Ts(Long(sub, "timemodified")) : null;

            // Una nota nula nunca es 0. Si hay nota: graded; si entregó sin nota: pending_grading; si no: not_submitted.
            var status = score != null ? "graded"
                       : submission == "submitted" ? "pending_grading"
                       : "not_submitted";

            gradeList.Add(new(st.Id, a.Cmid, a.Name, status, submission, score, max, submittedAt, gradedAt));

            // Estado de finalización: sin seguimiento configurado o sin dato = not_available (nunca null ni 0)
            var completion = "not_available";
            if (byCmid.TryGetValue(a.Cmid, out var v) && v.Tracking != 0)
                completion = v.State switch
                {
                    0 => "incomplete",
                    1 => "complete",
                    2 => "passed",
                    3 => "failed",
                    _ => "not_available",
                };
            progList.Add(new(a.Cmid, "assign", completion));
        }
        details.Add(new(st, gradeList, progList));
    }

    var course = new CourseOut(cid, shortName, fullName, students.Count, DateTimeOffset.UtcNow, details);

    // Resumen en consola (solo ids, sin nombres)
    Console.WriteLine($"\nCurso {cid} ({shortName}): {students.Count} estudiantes, {assigns.Count} tareas");
    foreach (var d in details)
        foreach (var g in d.Grades)
        {
            var comp2 = d.Activities.First(x => x.ActivityId == g.ActivityId).CompletionState;
            var score = g.Score is double sc ? $"{sc:0.##}/{g.MaxScore:0.##}" : $"-/{g.MaxScore:0.##}";
            Console.WriteLine($"  est {d.Student.Id,2} | {g.ActivityName,-8} | {g.Status,-15} | {g.SubmissionStatus,-9} | {score,-8} | {comp2}");
        }
    foreach (var w in warnings) Console.WriteLine("  AVISO: " + w);

    var json = JsonSerializer.Serialize(course, jsonOptions);
    var file = $"salida-curso-{cid}.json";
    File.WriteAllText(file, json);
    Console.WriteLine($"Guardado: {Path.GetFullPath(file)}");
    Console.WriteLine("Texto de las entregas (onlinetext) en la salida: " +
        (json.Contains("onlinetext", StringComparison.OrdinalIgnoreCase) ? "SI (error)" : "no"));
}

// ---------- Programa principal ----------
async Task Run()
{
    var sw = Stopwatch.StartNew();
    var info = await Call("core_webservice_get_site_info");
    var userId = info.GetProperty("userid").GetInt32();
    Console.WriteLine($"Moodle {Str(info, "release")} | usuario {Str(info, "username")} (id {userId})");

    var courses = await Call("core_enrol_get_users_courses", ("userid", userId.ToString()));
    foreach (var c in courses.EnumerateArray())
        await SyncCourse(c.GetProperty("id").GetInt32(), Str(c, "shortname") ?? "", Str(c, "fullname") ?? "");

    Console.WriteLine($"\nTiempo total: {sw.Elapsed.TotalSeconds:F1} s");
}

try
{
    await Run();
}
catch (Exception ex)
{
    Console.WriteLine("ERROR: " + ex.Message);
    Environment.ExitCode = 1;
}

// ---------- Tipos de salida (forma de StudentDetail y GradeEntry del contrato) ----------
record StudentOut(int Id, string FullName, string? Email);
record GradeOut(int StudentId, int ActivityId, string ActivityName, string Status, string SubmissionStatus,
                double? Score, double MaxScore, DateTimeOffset? SubmittedAt, DateTimeOffset? GradedAt);
record ProgressOut(int ActivityId, string ActivityType, string CompletionState);
record StudentDetailOut(StudentOut Student, List<GradeOut> Grades, List<ProgressOut> Activities);
record CourseOut(int Id, string ShortName, string FullName, int StudentCount, DateTimeOffset LastSyncAt,
                 List<StudentDetailOut> Students);
