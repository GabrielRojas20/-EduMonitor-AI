using System.Collections.Concurrent;
using Microsoft.Data.SqlClient;

namespace MoodleSync.Api;

// Almacenamiento persistente de Moodle Sync en SQL Server.
// El texto de las entregas (onlinetext) nunca forma parte de CourseSnapshot
// y por tanto nunca se escribe en la base de datos.
public sealed class SqlSyncStore : ISyncStore
{
    private readonly string _connectionString;
    private readonly ConcurrentDictionary<int, SyncStatusDto> _runningStatuses = new();

    public SqlSyncStore(IConfiguration configuration)
    {
        _connectionString = configuration.GetConnectionString("EduMonitor")
            ?? throw new InvalidOperationException(
                "Falta ConnectionStrings__EduMonitor en la configuración.");
    }

    public async Task<CourseSnapshot?> GetSnapshotAsync(int courseId)
    {
        await using var connection = new SqlConnection(_connectionString);
        await connection.OpenAsync();

        string shortName;
        string fullName;
        DateTime syncedAt;

        await using (var command = new SqlCommand("""
            SELECT short_name, full_name, last_sync_at
            FROM sync.course
            WHERE course_id = @courseId
            """, connection))
        {
            command.Parameters.AddWithValue("@courseId", courseId);
            await using var reader = await command.ExecuteReaderAsync();
            if (!await reader.ReadAsync() || reader.IsDBNull(2)) return null;
            shortName = reader.GetString(0);
            fullName = reader.GetString(1);
            syncedAt = reader.GetDateTime(2);
        }

        var latestGradeSyncId = await LatestSyncIdAsync(connection, "sync.grade", "synced_at", courseId);
        var latestCompletionSyncId = await LatestSyncIdAsync(connection, "sync.completion", "observed_at", courseId);

        var students = new List<StudentDto>();
        await using (var command = new SqlCommand("""
            SELECT DISTINCT s.student_id, s.full_name, s.email
            FROM sync.student s
            WHERE s.student_id IN (
                SELECT student_id FROM sync.grade WHERE course_id = @courseId
                UNION
                SELECT student_id FROM sync.completion WHERE course_id = @courseId
            )
            ORDER BY s.student_id
            """, connection))
        {
            command.Parameters.AddWithValue("@courseId", courseId);
            await using var reader = await command.ExecuteReaderAsync();
            while (await reader.ReadAsync())
            {
                students.Add(new StudentDto(
                    reader.GetInt32(0),
                    reader.GetString(1),
                    reader.IsDBNull(2) ? null : reader.GetString(2)));
            }
        }

        var grades = new List<GradeEntryDto>();
        if (latestGradeSyncId is not null)
        {
            await using var command = new SqlCommand("""
                SELECT student_id, activity_id, status, submission_status, score, max_score
                FROM sync.grade
                WHERE course_id = @courseId AND sync_id = @syncId
                ORDER BY student_id, activity_id
                """, connection);
            command.Parameters.AddWithValue("@courseId", courseId);
            command.Parameters.AddWithValue("@syncId", latestGradeSyncId);
            await using var reader = await command.ExecuteReaderAsync();
            while (await reader.ReadAsync())
            {
                grades.Add(new GradeEntryDto(
                    reader.GetInt32(0),
                    reader.GetInt32(1),
                    "Actividad " + reader.GetInt32(1),
                    reader.GetString(2),
                    reader.GetString(3),
                    reader.IsDBNull(4) ? null : (double)reader.GetDecimal(4),
                    (double)reader.GetDecimal(5),
                    null,
                    null));
            }
        }

        var progress = new Dictionary<int, List<ActivityProgressDto>>();
        if (latestCompletionSyncId is not null)
        {
            await using var command = new SqlCommand("""
                SELECT student_id, activity_id, state
                FROM sync.completion
                WHERE course_id = @courseId AND sync_id = @syncId
                ORDER BY student_id, activity_id
                """, connection);
            command.Parameters.AddWithValue("@courseId", courseId);
            command.Parameters.AddWithValue("@syncId", latestCompletionSyncId);
            await using var reader = await command.ExecuteReaderAsync();
            while (await reader.ReadAsync())
            {
                var studentId = reader.GetInt32(0);
                if (!progress.ContainsKey(studentId)) progress[studentId] = new List<ActivityProgressDto>();
                progress[studentId].Add(new ActivityProgressDto(
                    reader.GetInt32(1), "assign", reader.GetString(2)));
            }
        }

        var readOnlyProgress = progress.ToDictionary(
            pair => pair.Key,
            pair => (IReadOnlyList<ActivityProgressDto>)pair.Value);

        return new CourseSnapshot(
            courseId,
            shortName,
            fullName,
            new DateTimeOffset(syncedAt, TimeSpan.Zero),
            students,
            grades,
            readOnlyProgress);
    }

    public async Task SaveSnapshotAsync(CourseSnapshot snapshot)
    {
        await using var connection = new SqlConnection(_connectionString);
        await connection.OpenAsync();
        await using var transaction = (SqlTransaction)await connection.BeginTransactionAsync();

        try
        {
            await ExecuteAsync(connection, transaction, """
                IF EXISTS (SELECT 1 FROM sync.course WHERE course_id = @courseId)
                    UPDATE sync.course
                    SET short_name = @shortName, full_name = @fullName, last_sync_at = @syncedAt
                    WHERE course_id = @courseId
                ELSE
                    INSERT INTO sync.course (course_id, short_name, full_name, last_sync_at)
                    VALUES (@courseId, @shortName, @fullName, @syncedAt)
                """,
                ("@courseId", snapshot.CourseId),
                ("@shortName", snapshot.ShortName),
                ("@fullName", snapshot.FullName),
                ("@syncedAt", snapshot.SyncedAt.UtcDateTime));

            foreach (var student in snapshot.Students)
            {
                await ExecuteAsync(connection, transaction, """
                    IF EXISTS (SELECT 1 FROM sync.student WHERE student_id = @studentId)
                        UPDATE sync.student SET full_name = @fullName, email = @email
                        WHERE student_id = @studentId
                    ELSE
                        INSERT INTO sync.student (student_id, full_name, email)
                        VALUES (@studentId, @fullName, @email)
                    """,
                    ("@studentId", student.Id),
                    ("@fullName", student.FullName),
                    ("@email", (object?)student.Email ?? DBNull.Value));
            }

            var syncId = Guid.NewGuid().ToString("N");
            foreach (var grade in snapshot.Grades)
            {
                await ExecuteAsync(connection, transaction, """
                    INSERT INTO sync.grade
                        (course_id, student_id, activity_id, status, submission_status,
                         score, max_score, sync_id, synced_at)
                    VALUES
                        (@courseId, @studentId, @activityId, @status, @submissionStatus,
                         @score, @maxScore, @syncId, @syncedAt)
                    """,
                    ("@courseId", snapshot.CourseId),
                    ("@studentId", grade.StudentId),
                    ("@activityId", grade.ActivityId),
                    ("@status", grade.Status),
                    ("@submissionStatus", grade.SubmissionStatus),
                    ("@score", (object?)grade.Score ?? DBNull.Value),
                    ("@maxScore", grade.MaxScore),
                    ("@syncId", syncId),
                    ("@syncedAt", snapshot.SyncedAt.UtcDateTime));
            }

            foreach (var entry in snapshot.Progress)
            {
                foreach (var activity in entry.Value)
                {
                    await ExecuteAsync(connection, transaction, """
                        INSERT INTO sync.completion
                            (course_id, student_id, activity_id, state, sync_id, observed_at)
                        VALUES
                            (@courseId, @studentId, @activityId, @state, @syncId, @observedAt)
                        """,
                        ("@courseId", snapshot.CourseId),
                        ("@studentId", entry.Key),
                        ("@activityId", activity.ActivityId),
                        ("@state", activity.CompletionState),
                        ("@syncId", syncId),
                        ("@observedAt", snapshot.SyncedAt.UtcDateTime));
                }
            }

            await transaction.CommitAsync();
        }
        catch
        {
            await transaction.RollbackAsync();
            throw;
        }
    }

    public async Task<SyncStatusDto?> GetStatusAsync(int courseId)
    {
        if (_runningStatuses.TryGetValue(courseId, out var current)) return current;

        await using var connection = new SqlConnection(_connectionString);
        await connection.OpenAsync();
        await using var command = new SqlCommand(
            "SELECT last_sync_at FROM sync.course WHERE course_id = @courseId", connection);
        command.Parameters.AddWithValue("@courseId", courseId);
        var value = await command.ExecuteScalarAsync();

        return value is DateTime date
            ? new SyncStatusDto("succeeded", null, date, date, null, null)
            : null;
    }

    public Task SaveStatusAsync(int courseId, SyncStatusDto status)
    {
        _runningStatuses[courseId] = status;
        return Task.CompletedTask;
    }

    private static async Task<string?> LatestSyncIdAsync(
        SqlConnection connection, string table, string timestampColumn, int courseId)
    {
        await using var command = new SqlCommand($"""
            SELECT TOP 1 sync_id FROM {table}
            WHERE course_id = @courseId
            ORDER BY {timestampColumn} DESC
            """, connection);
        command.Parameters.AddWithValue("@courseId", courseId);
        var value = await command.ExecuteScalarAsync();
        return value as string;
    }

    private static async Task ExecuteAsync(
        SqlConnection connection,
        SqlTransaction transaction,
        string sql,
        params (string Name, object Value)[] parameters)
    {
        await using var command = new SqlCommand(sql, connection, transaction);
        foreach (var (name, value) in parameters) command.Parameters.AddWithValue(name, value);
        await command.ExecuteNonQueryAsync();
    }
}
