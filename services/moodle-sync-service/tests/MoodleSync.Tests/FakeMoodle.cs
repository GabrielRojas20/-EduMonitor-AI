using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace MoodleSync.Tests;

// Moodle falso, con los mismos datos que el curso de prueba real (S1-06): 5 estudiantes y 2 tareas.
// Todos los datos son ficticios.
public sealed class FakeMoodle : IDisposable
{
    public const string Token = "token-de-prueba";
    public const string SecretoDeLaEntrega = "TEXTO-SECRETO-DE-LA-ENTREGA";

    private readonly WebApplication _app;
    public string Url => _app.Urls.First().TrimEnd('/');

    // Configuración de cada prueba
    public TimeSpan Delay { get; set; } = TimeSpan.Zero;          // retraso en core_enrol_get_enrolled_users
    public HashSet<string> Failing { get; } = new();              // funciones que responden con un error de Moodle
    public List<string> Queries { get; } = new();                 // query string de cada petición (debe estar vacío)
    public int RequestsWithoutToken;                              // peticiones sin wstoken en el cuerpo

    public FakeMoodle()
    {
        var b = WebApplication.CreateBuilder();
        b.WebHost.UseUrls("http://127.0.0.1:0");
        b.Logging.ClearProviders();
        _app = b.Build();
        _app.MapPost("/webservice/rest/server.php", async (HttpRequest req) =>
        {
            lock (Queries) Queries.Add(req.QueryString.Value ?? "");
            var form = await req.ReadFormAsync();
            var fn = form["wsfunction"].ToString();
            if (form["wstoken"].ToString() != Token)
            {
                Interlocked.Increment(ref RequestsWithoutToken);
                return Json(new { exception = "moodle_exception", errorcode = "invalidtoken", message = "Invalid token - token not found" });
            }
            if (fn == "core_enrol_get_enrolled_users" && Delay > TimeSpan.Zero) await Task.Delay(Delay);
            if (Failing.Contains(fn))
                return Json(new { exception = "webservice_access_exception", errorcode = "accessexception", message = "Access control exception" });
            return Json(Respond(fn, form));
        });
        _app.StartAsync().GetAwaiter().GetResult();
    }

    private static IResult Json(object data) => Results.Text(JsonSerializer.Serialize(data), "application/json");

    private static object Respond(string fn, IFormCollection form) => fn switch
    {
        "core_webservice_get_site_info" => new { userid = 3, username = "docente1", release = "5.2.4 (Build: 20261005)" },
        "core_enrol_get_users_courses" => new[] { new { id = 2, shortname = "PRUEBA01", fullname = "Curso de Prueba EduMonitor" } },
        "core_enrol_get_enrolled_users" => Users(),
        "mod_assign_get_assignments" => new
        {
            courses = new[]
            {
                new
                {
                    id = 2,
                    assignments = new object[]
                    {
                        new { id = 1, cmid = 2, name = "Tarea 1", grade = 10 },
                        new { id = 2, cmid = 3, name = "Tarea 2", grade = 100 },
                    },
                },
            },
            warnings = Array.Empty<object>(),
        },
        "gradereport_user_get_grade_items" => GradeItems(),
        "mod_assign_get_submissions" => Submissions(),
        "core_completion_get_activities_completion_status" => Completion(int.Parse(form["userid"].ToString())),
        _ => new { exception = "moodle_exception", errorcode = "invalidfunction", message = "Función desconocida" },
    };

    private static readonly (int Id, string Name)[] Students =
    {
        (4, "Estudiante Uno"), (5, "Estudiante Dos"), (6, "Estudiante Tres"), (7, "Estudiante Cuatro"), (8, "Estudiante Cinco"),
    };

    private static object[] Users()
    {
        var list = new List<object>
        {
            new { id = 3, fullname = "Docente Prueba", email = "docente1@example.com", roles = new[] { new { roleid = 3, shortname = "editingteacher" } } },
        };
        foreach (var (id, name) in Students)
            list.Add(new { id, fullname = name, email = $"estudiante{id - 3}@example.com", roles = new[] { new { roleid = 5, shortname = "student" } } });
        return list.ToArray();
    }

    // Notas (Tarea 1 sobre 10, Tarea 2 sobre 100). null = sin nota.
    private static readonly Dictionary<int, (double? T1, double? T2)> Scores = new()
    {
        [4] = (8, null), [5] = (0, 90), [6] = (null, null), [7] = (null, null), [8] = (5, null),
    };

    private static object Item(int cmid, string name, double? raw, double max) => new
    {
        itemtype = "mod", itemmodule = "assign", itemname = name, cmid, graderaw = raw, grademax = max,
        gradedategraded = raw is null ? (long?)null : 1792554536L,
    };

    private static object GradeItems()
    {
        var users = Students.Select(s => new
        {
            userid = s.Id,
            userfullname = s.Name,
            gradeitems = new object[]
            {
                Item(2, "Tarea 1", Scores[s.Id].T1, 10),
                Item(3, "Tarea 2", Scores[s.Id].T2, 100),
                new { itemtype = "course", itemmodule = (string?)null, graderaw = Scores[s.Id].T1, grademax = 10 },
            },
        });
        return new { usergrades = users.ToArray(), warnings = Array.Empty<object>() };
    }

    private static object Sub(int user, string status, string grading, long modified) => new
    {
        id = user, userid = user, status, gradingstatus = grading, timemodified = modified,
        plugins = new object[]
        {
            new { type = "onlinetext", name = "Online text",
                  editorfields = new[] { new { name = "onlinetext", text = "<p>" + SecretoDeLaEntrega + "</p>", format = 1 } } },
        },
    };

    private static object Submissions() => new
    {
        assignments = new object[]
        {
            new { assignmentid = 1, submissions = new object[]
                { Sub(4, "submitted", "graded", 1792554518), Sub(5, "submitted", "graded", 1792554567),
                  Sub(6, "submitted", "notgraded", 1792554618), Sub(8, "submitted", "graded", 1792554637) } },
            new { assignmentid = 2, submissions = new object[]
                { Sub(4, "draft", "notgraded", 1792554700), Sub(5, "submitted", "graded", 1792554720) } },
        },
        warnings = Array.Empty<object>(),
    };

    // Estado de finalización por estudiante (Tarea 1, Tarea 2): 0 incompleta, 1 completa.
    private static readonly Dictionary<int, (int T1, int T2)> Comp = new()
    {
        [4] = (1, 0), [5] = (1, 1), [6] = (0, 0), [7] = (0, 0), [8] = (1, 0),
    };

    private static object Completion(int userId)
    {
        var c = Comp.TryGetValue(userId, out var v) ? v : (0, 0);
        return new
        {
            statuses = new object[]
            {
                new { cmid = 2, modname = "assign", state = c.Item1, tracking = 2 },
                new { cmid = 3, modname = "assign", state = c.Item2, tracking = 2 },
            },
            warnings = Array.Empty<object>(),
        };
    }

    public void Dispose() => _app.StopAsync().GetAwaiter().GetResult();
}
