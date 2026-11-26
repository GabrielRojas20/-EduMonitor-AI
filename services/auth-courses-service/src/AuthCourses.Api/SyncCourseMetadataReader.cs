using Microsoft.Data.SqlClient;

namespace AuthCourses.Api;

public sealed record SyncCourseMetadata(int StudentCount, DateTimeOffset? LastSyncAt);

public interface ISyncCourseMetadataReader
{
    Task<IReadOnlyDictionary<int, SyncCourseMetadata>> GetAsync(
        IReadOnlyCollection<int> courseIds, CancellationToken cancellationToken = default);
}

public sealed class SqlSyncCourseMetadataReader(IConfiguration configuration) : ISyncCourseMetadataReader
{
    private readonly string? _connectionString =
        configuration.GetConnectionString("EduMonitor");

    public async Task<IReadOnlyDictionary<int, SyncCourseMetadata>> GetAsync(
        IReadOnlyCollection<int> courseIds, CancellationToken cancellationToken = default)
    {
        if (courseIds.Count == 0 || string.IsNullOrWhiteSpace(_connectionString))
            return new Dictionary<int, SyncCourseMetadata>();

        await using var connection = new SqlConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        await using var command = connection.CreateCommand();
        command.CommandText = """
            WITH snapshot_candidates AS (
                SELECT course_id, sync_id, MAX(synced_at) AS snapshot_at
                FROM sync.grade
                WHERE course_id IN (SELECT value FROM STRING_SPLIT(@courseIds, ','))
                GROUP BY course_id, sync_id
                UNION ALL
                SELECT course_id, sync_id, MAX(observed_at) AS snapshot_at
                FROM sync.completion
                WHERE course_id IN (SELECT value FROM STRING_SPLIT(@courseIds, ','))
                GROUP BY course_id, sync_id
            ),
            snapshot_groups AS (
                SELECT course_id, sync_id, MAX(snapshot_at) AS snapshot_at
                FROM snapshot_candidates
                GROUP BY course_id, sync_id
            ),
            latest_sync AS (
                SELECT course_id, sync_id,
                       ROW_NUMBER() OVER (
                           PARTITION BY course_id
                           ORDER BY snapshot_at DESC, sync_id DESC
                       ) AS row_number
                FROM snapshot_groups
            ),
            linked_students AS (
                SELECT g.course_id, g.student_id
                FROM sync.grade g
                INNER JOIN latest_sync latest
                    ON latest.course_id = g.course_id
                   AND latest.sync_id = g.sync_id
                   AND latest.row_number = 1
                UNION
                SELECT c.course_id, c.student_id
                FROM sync.completion c
                INNER JOIN latest_sync latest
                    ON latest.course_id = c.course_id
                    AND latest.sync_id = c.sync_id
                   AND latest.row_number = 1
            )
            SELECT c.course_id,
                   COUNT(DISTINCT ls.student_id) AS student_count,
                   c.last_sync_at
            FROM sync.course c
            LEFT JOIN linked_students ls ON ls.course_id = c.course_id
            WHERE c.course_id IN (SELECT value FROM STRING_SPLIT(@courseIds, ','))
            GROUP BY c.course_id, c.last_sync_at;
            """;
        command.Parameters.AddWithValue("@courseIds", string.Join(',', courseIds));

        var result = new Dictionary<int, SyncCourseMetadata>();
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            var courseId = reader.GetInt32(0);
            var count = reader.GetInt32(1);
            DateTimeOffset? lastSyncAt = null;
            if (!reader.IsDBNull(2))
            {
                var value = DateTime.SpecifyKind(reader.GetDateTime(2), DateTimeKind.Utc);
                lastSyncAt = new DateTimeOffset(value);
            }
            result[courseId] = new SyncCourseMetadata(count, lastSyncAt);
        }

        return result;
    }
}
