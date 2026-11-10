using System.Collections.Concurrent;

namespace MoodleSync.Api;

// Dónde se guarda lo sincronizado. Hoy: memoria. Cuando esté el esquema sync de Gabriel, se agrega una versión con SQL Server.
public interface ISyncStore
{
    Task<CourseSnapshot?> GetSnapshotAsync(int courseId);
    Task SaveSnapshotAsync(CourseSnapshot snapshot);
    Task<SyncStatusDto?> GetStatusAsync(int courseId);
    Task SaveStatusAsync(int courseId, SyncStatusDto status);
}

public sealed class InMemorySyncStore : ISyncStore
{
    private readonly ConcurrentDictionary<int, CourseSnapshot> _snapshots = new();
    private readonly ConcurrentDictionary<int, SyncStatusDto> _statuses = new();

    public Task<CourseSnapshot?> GetSnapshotAsync(int courseId)
        => Task.FromResult(_snapshots.TryGetValue(courseId, out var s) ? s : null);

    public Task SaveSnapshotAsync(CourseSnapshot snapshot)
    {
        _snapshots[snapshot.CourseId] = snapshot;
        return Task.CompletedTask;
    }

    public Task<SyncStatusDto?> GetStatusAsync(int courseId)
        => Task.FromResult(_statuses.TryGetValue(courseId, out var s) ? s : null);

    public Task SaveStatusAsync(int courseId, SyncStatusDto status)
    {
        _statuses[courseId] = status;
        return Task.CompletedTask;
    }
}

public sealed record StartResult(string Outcome, string? SyncId = null, string? Detail = null); // accepted | conflict | unavailable

public sealed class SyncService(MoodleClient moodle, ISyncStore store, ILogger<SyncService> log)
{
    private readonly object _gate = new();
    private readonly HashSet<int> _running = new();

    public async Task<StartResult> StartAsync(int courseId)
    {
        lock (_gate)
        {
            if (!_running.Add(courseId)) return new StartResult("conflict");
        }

        try
        {
            // Comprobación rápida: si Moodle no responde, se avisa de inmediato con un 503.
            await moodle.CallAsync("core_webservice_get_site_info", CancellationToken.None);

            var previous = await store.GetStatusAsync(courseId);
            var started = DateTimeOffset.UtcNow;
            await store.SaveStatusAsync(courseId, new SyncStatusDto("running", started, null, previous?.LastSuccessAt, null, null));
            _ = Task.Run(() => RunAsync(courseId, started, previous?.LastSuccessAt));
            return new StartResult("accepted", Guid.NewGuid().ToString("N"));
        }
        catch (MoodleUnavailableException ex)
        {
            Release(courseId);
            return new StartResult("unavailable", Detail: ex.Message);
        }
        catch (MoodleApiException ex)
        {
            Release(courseId);
            return new StartResult("unavailable", Detail: $"Moodle rechazó el acceso del servicio ({ex.ErrorCode}).");
        }
        catch
        {
            Release(courseId);
            throw;
        }
    }

    private void Release(int courseId)
    {
        lock (_gate) _running.Remove(courseId);
    }

    private async Task RunAsync(int courseId, DateTimeOffset started, DateTimeOffset? lastSuccess)
    {
        SyncStatusDto result;
        try
        {
            var snapshot = await FetchAsync(courseId, CancellationToken.None);
            await store.SaveSnapshotAsync(snapshot);
            var finished = DateTimeOffset.UtcNow;
            result = new SyncStatusDto("succeeded", started, finished, finished, null, null);
        }
        catch (MoodleUnavailableException ex)
        {
            result = Failed(started, lastSuccess, "MOODLE_UNAVAILABLE", ex.Message);
        }
        catch (MoodleApiException ex)
        {
            result = Failed(started, lastSuccess, "MOODLE_ERROR", $"Moodle respondió con el error '{ex.ErrorCode}'.");
        }
        catch (CourseNotFoundInMoodleException ex)
        {
            result = Failed(started, lastSuccess, "COURSE_NOT_IN_MOODLE", ex.Message);
        }
        catch (Exception ex)
        {
            log.LogError(ex, "Error inesperado al sincronizar el curso {CourseId}", courseId);
            result = Failed(started, lastSuccess, "UNEXPECTED", "Error inesperado al sincronizar.");
        }

        try
        {
            await store.SaveStatusAsync(courseId, result);
        }
        finally
        {
            Release(courseId);
        }
    }

    private static SyncStatusDto Failed(DateTimeOffset started, DateTimeOffset? lastSuccess, string code, string message)
        => new("failed", started, DateTimeOffset.UtcNow, lastSuccess, code, message);

    private async Task<CourseSnapshot> FetchAsync(int courseId, CancellationToken ct)
    {
        var cid = courseId.ToString();

        var info = await moodle.CallAsync("core_webservice_get_site_info", ct);
        var userId = J.Int(info, "userid") ?? throw new MoodleApiException("invalid_response", "Moodle no devolvió el usuario del servicio.");

        var courses = await moodle.CallAsync("core_enrol_get_users_courses", ct, ("userid", userId.ToString()));
        var course = courses.ValueKind == System.Text.Json.JsonValueKind.Array
            ? courses.EnumerateArray().FirstOrDefault(c => J.Int(c, "id") == courseId)
            : default;
        if (course.ValueKind != System.Text.Json.JsonValueKind.Object) throw new CourseNotFoundInMoodleException(courseId);

        var students = Normalizer.ParseStudents(await moodle.CallAsync("core_enrol_get_enrolled_users", ct, ("courseid", cid)));
        var assignments = Normalizer.ParseAssignments(await moodle.CallAsync("mod_assign_get_assignments", ct, ("courseids[0]", cid)));
        var grades = Normalizer.ParseGrades(await moodle.CallAsync("gradereport_user_get_grade_items", ct, ("courseid", cid)));

        var submissions = new Dictionary<(int AssignId, int User), SubmissionInfo>();
        if (assignments.Count > 0)
        {
            var ps = assignments.Select((a, i) => ($"assignmentids[{i}]", a.Id.ToString())).ToArray();
            submissions = Normalizer.ParseSubmissions(await moodle.CallAsync("mod_assign_get_submissions", ct, ps));
        }

        // Moodle solo acepta un userid por llamada: se consultan varios estudiantes a la vez.
        var completion = new ConcurrentDictionary<int, Dictionary<int, CompletionInfo>>();
        await Parallel.ForEachAsync(students, new ParallelOptions { MaxDegreeOfParallelism = 4, CancellationToken = ct }, async (st, token) =>
        {
            var raw = await moodle.CallAsync("core_completion_get_activities_completion_status", token,
                ("courseid", cid), ("userid", st.Id.ToString()));
            completion[st.Id] = Normalizer.ParseCompletion(raw);
        });

        var warnings = new List<string>();
        var allGrades = new List<GradeEntryDto>();
        var progress = new Dictionary<int, IReadOnlyList<ActivityProgressDto>>();
        foreach (var st in students)
        {
            var comp = completion.TryGetValue(st.Id, out var c) ? c : new Dictionary<int, CompletionInfo>();
            var (g, p) = Normalizer.Build(st, assignments, grades, submissions, comp, warnings);
            allGrades.AddRange(g);
            progress[st.Id] = p;
        }
        foreach (var w in warnings) log.LogWarning("{Warning}", w);

        return new CourseSnapshot(courseId, J.Str(course, "shortname") ?? "", J.Str(course, "fullname") ?? "",
            DateTimeOffset.UtcNow, students, allGrades, progress);
    }
}
