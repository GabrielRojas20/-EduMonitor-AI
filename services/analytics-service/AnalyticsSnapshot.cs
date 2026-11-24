namespace EduMonitor.Analytics;

public readonly record struct SyncObservation(string SyncId, DateTime ObservedAt);

public static class AnalyticsSnapshotSelector
{
    public static string? LatestSyncId(IEnumerable<SyncObservation> observations)
    {
        return observations
            .Where(x => !string.IsNullOrWhiteSpace(x.SyncId))
            .GroupBy(x => x.SyncId, StringComparer.Ordinal)
            .Select(group => new
            {
                SyncId = group.Key,
                LastObservedAt = group.Max(x => x.ObservedAt),
            })
            .OrderByDescending(x => x.LastObservedAt)
            .ThenByDescending(x => x.SyncId, StringComparer.Ordinal)
            .Select(x => x.SyncId)
            .FirstOrDefault();
    }
}
