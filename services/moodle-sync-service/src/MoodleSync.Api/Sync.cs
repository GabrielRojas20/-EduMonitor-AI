using System.Collections.Concurrent;

namespace MoodleSync.Api;

// Dónde se guarda lo sincronizado. Hoy: memoria. Cuando esté el esquema sync de Gabriel, se agrega una versión con SQL Server.
public interface ISyncStore
{
    Task<CourseSnapshot?> GetSnapshotAsync(int courseId);
    Task SaveSnapshotAsync(CourseSnapshot snapshot, string syncId);
    Task<SyncStatusDto?> GetStatusAsync(int courseId);
    Task SaveStatusAsync(int courseId, SyncStatusDto status);
    Task StartAuditAsync(SyncAuditRecord audit);
    Task FinishAuditAsync(string syncId, SyncAuditRecord completed);
    Task<IReadOnlyList<SyncAuditRecord>> GetAuditHistoryAsync(int courseId, int limit);
}

public sealed class InMemorySyncStore : ISyncStore
{
    private readonly ConcurrentDictionary<int, CourseSnapshot> _snapshots = new();
    private readonly ConcurrentDictionary<int, SyncStatusDto> _statuses = new();
    private readonly ConcurrentDictionary<string, SyncAuditRecord> _audits = new();

    public Task<CourseSnapshot?> GetSnapshotAsync(int courseId)
        => Task.FromResult(_snapshots.TryGetValue(courseId, out var s) ? s : null);

    public Task SaveSnapshotAsync(CourseSnapshot snapshot, string syncId)
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

    public Task StartAuditAsync(SyncAuditRecord audit)
    {
        _audits[audit.SyncId] = audit;
        return Task.CompletedTask;
    }

    public Task FinishAuditAsync(string syncId, SyncAuditRecord completed)
    {
        _audits[syncId] = completed;
        return Task.CompletedTask;
    }

    public Task<IReadOnlyList<SyncAuditRecord>> GetAuditHistoryAsync(int courseId, int limit)
    {
        IReadOnlyList<SyncAuditRecord> result = _audits.Values
            .Where(x => x.CourseId == courseId)
            .OrderByDescending(x => x.StartedAt)
            .Take(limit)
            .ToList();
        return Task.FromResult(result);
    }
}

public sealed record StartResult(string Outcome, string? SyncId = null, string? Detail = null); // accepted | conflict | unavailable

public sealed class SyncService(MoodleClient moodle, ISyncStore store, ILogger<SyncService> log)
{
    private readonly object _gate = new();
    private readonly HashSet<int> _running = new();

    public async Task<StartResult> StartAsync(int courseId, string userId)
    {
        lock (_gate)
        {
            if (!_running.Add(courseId)) return new StartResult("conflict");
        }

        var syncId = Guid.NewGuid().ToString("N");
        var started = DateTimeOffset.UtcNow;
        var audit = new SyncAuditRecord(syncId, courseId, userId, started, null, "running", null);
        var handedOff = false;
        try
        {
            try
            {
                await store.StartAuditAsync(audit);
            }
            catch (Exception ex)
            {
                log.LogError(ex, "No se pudo iniciar la auditoría de la sincronización {SyncId}", syncId);
            }

            // Comprobación rápida: si Moodle no responde, se avisa de inmediato con un 503.
            await moodle.CallAsync("core_webservice_get_site_info", CancellationToken.None);

            var previous = await store.GetStatusAsync(courseId);
            await store.SaveStatusAsync(courseId, new SyncStatusDto("running", started, null, previous?.LastSuccessAt, null, null));
            _ = Task.Run(() => RunAsync(courseId, syncId, userId, started, previous?.LastSuccessAt));
            handedOff = true;
            return new StartResult("accepted", syncId);
        }
        catch (MoodleUnavailableException ex)
        {
            await TryFinishAuditAsync(audit with { State = "failed" }, "MOODLE_UNAVAILABLE");
            return new StartResult("unavailable", syncId, ex.Message);
        }
        catch (MoodleApiException ex)
        {
            await TryFinishAuditAsync(audit with { State = "failed" }, ex.ErrorCode);
            return new StartResult("unavailable", syncId, $"Moodle rechazó el acceso del servicio ({ex.ErrorCode}).");
        }
        catch
        {
            await TryFinishAuditAsync(audit with { State = "failed" }, "UNEXPECTED");
            throw;
        }
        finally
        {
            if (!handedOff) Release(courseId);
        }
    }

    private async Task TryFinishAuditAsync(SyncAuditRecord audit, string? errorCode)
    {
        try
        {
            await store.FinishAuditAsync(audit.SyncId,
                audit with
                {
                    FinishedAt = DateTimeOffset.UtcNow,
                    ErrorCode = errorCode,
                });
        }
        catch (Exception ex)
        {
            log.LogError(ex, "No se pudo cerrar la auditoría de la sincronización {SyncId}", audit.SyncId);
        }
    }

    private void Release(int courseId)
    {
        lock (_gate) _running.Remove(courseId);
    }

    private async Task RunAsync(int courseId, string syncId, string userId, DateTimeOffset started, DateTimeOffset? lastSuccess)
    {
        SyncStatusDto result;
        try
        {
            try
            {
                var snapshot = await FetchAsync(courseId, CancellationToken.None);
                await store.SaveSnapshotAsync(snapshot, syncId);
                var finished = DateTimeOffset.UtcNow;
                result = new SyncStatusDto("succeeded", started, finished, finished, null, null);
                await TryFinishAuditAsync(
                    new SyncAuditRecord(syncId, courseId, userId, started, finished, "succeeded", null), null);
            }
            catch (MoodleUnavailableException ex)
            {
                result = Failed(started, lastSuccess, "MOODLE_UNAVAILABLE", ex.Message);
                await TryFinishAuditAsync(
                    new SyncAuditRecord(syncId, courseId, userId, started, null, "failed", result.ErrorCode),
                    result.ErrorCode);
            }
            catch (MoodleApiException ex)
            {
                result = Failed(started, lastSuccess, "MOODLE_ERROR", $"Moodle respondió con el error '{ex.ErrorCode}'.");
                await TryFinishAuditAsync(
                    new SyncAuditRecord(syncId, courseId, userId, started, null, "failed", result.ErrorCode),
                    result.ErrorCode);
            }
            catch (CourseNotFoundInMoodleException ex)
            {
                result = Failed(started, lastSuccess, "COURSE_NOT_IN_MOODLE", ex.Message);
                await TryFinishAuditAsync(
                    new SyncAuditRecord(syncId, courseId, userId, started, null, "failed", result.ErrorCode),
                    result.ErrorCode);
            }
            catch (Exception ex)
            {
                log.LogError(ex, "Error inesperado al sincronizar el curso {CourseId}", courseId);
                result = Failed(started, lastSuccess, "UNEXPECTED", "Error inesperado al sincronizar.");
                await TryFinishAuditAsync(
                    new SyncAuditRecord(syncId, courseId, userId, started, null, "failed", result.ErrorCode),
                    result.ErrorCode);
            }

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
        var info = await moodle.CallAsync("core_webservice_get_site_info", ct);
        var userId = J.Int(info, "userid") ?? throw new MoodleApiException("invalid_response", "Moodle no devolvió el usuario del servicio.");

        var courses = await moodle.CallAsync("core_enrol_get_users_courses", ct, ("userid", userId.ToString()));
        var availableCourses = courses.ValueKind == System.Text.Json.JsonValueKind.Array
            ? courses.EnumerateArray().ToArray()
            : Array.Empty<System.Text.Json.JsonElement>();
        var course = availableCourses.FirstOrDefault(c => J.Int(c, "id") == courseId);
        if (course.ValueKind != System.Text.Json.JsonValueKind.Object
            && CourseIdentity.MoodleShortName(courseId) is string expectedShortName)
        {
            course = availableCourses.FirstOrDefault(c =>
                string.Equals(J.Str(c, "shortname"), expectedShortName, StringComparison.OrdinalIgnoreCase));
        }
        if (course.ValueKind != System.Text.Json.JsonValueKind.Object) throw new CourseNotFoundInMoodleException(courseId);

        var moodleCourseId = J.Int(course, "id") ?? throw new MoodleApiException("invalid_response", "Moodle no devolvió el ID del curso.");
        var cid = moodleCourseId.ToString();
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

// Los IDs 201-225 pertenecen al seed masivo de Auth/Analytics. Moodle asigna
// sus propios IDs al importar el CSV, por lo que la sincronización usa el
// shortname estable para encontrar el curso real y conserva el ID de Auth en
// el snapshot guardado.
internal static class CourseIdentity
{
    public static string? MoodleShortName(int courseId) => courseId switch
    {
        2 => "PRUEBA01",
        3 => "PRUEBA02",
        >= 201 and <= 225 => $"DEMO-{(courseId - 201) / 5 + 1:00}-{(courseId - 201) % 5 + 1:00}",
        _ => null,
    };
}
