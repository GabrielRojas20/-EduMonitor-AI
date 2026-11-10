using System.Text.Json;
using MoodleSync.Api;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSingleton(sp => new JwtSettings(sp.GetRequiredService<IConfiguration>()));

// Validación del JWT que reenvía el gateway: firma, vencimiento, emisor y audiencia.
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer();
builder.Services.AddOptions<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme)
    .Configure<JwtSettings>((o, s) =>
    {
        o.MapInboundClaims = false;
        o.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidIssuer = s.Issuer,
            ValidateAudience = true,
            ValidAudience = s.Audience,
            ValidateLifetime = true,
            ClockSkew = TimeSpan.FromSeconds(30),
            ValidateIssuerSigningKey = true,
            IssuerSigningKey = s.Key,
            ValidAlgorithms = new[] { SecurityAlgorithms.HmacSha256 },
            NameClaimType = "name",
            RoleClaimType = "role",
        };
        o.Events = new JwtBearerEvents
        {
            OnChallenge = async c =>
            {
                c.HandleResponse();
                var expired = c.AuthenticateFailure is SecurityTokenExpiredException;
                c.Response.StatusCode = 401;
                await c.Response.WriteAsJsonAsync(
                    Problems.Build(c.HttpContext, 401, expired ? "TOKEN_EXPIRED" : "TOKEN_INVALID",
                        expired ? "El token venció" : "Token ausente o inválido"),
                    (JsonSerializerOptions?)null, "application/problem+json");
            },
        };
    });
builder.Services.AddAuthorization();

// Moodle: dirección y token vienen de variables de entorno (MOODLE_BASE_URL, MOODLE_WS_TOKEN). El token nunca va en la URL.
builder.Services.AddHttpClient("moodle", (sp, c) =>
{
    c.BaseAddress = new Uri(sp.GetRequiredService<IConfiguration>()["MOODLE_BASE_URL"] ?? "http://localhost:8080");
    c.Timeout = TimeSpan.FromSeconds(30);
});
builder.Services.AddSingleton<MoodleClient>();
builder.Services.AddSingleton<ISyncStore, SqlSyncStore>();
builder.Services.AddSingleton<SyncService>();

var app = builder.Build();

app.Services.GetRequiredService<JwtSettings>(); // falla al arrancar si falta JWT_SECRET

app.UseAuthentication();
app.UseAuthorization();

static PageDto<T> Slice<T>(IEnumerable<T> all, int? page, int? pageSize)
{
    var list = all.ToList();
    var p = Math.Max(page ?? 1, 1);
    var ps = Math.Clamp(pageSize ?? 50, 1, 200);
    return new PageDto<T>(list.Skip((p - 1) * ps).Take(ps).ToList(), p, ps, list.Count);
}

static IResult NotSynced(HttpContext ctx)
    => Problems.Result(ctx, 503, "DATA_NOT_AVAILABLE", "Los datos del curso aún no se sincronizaron",
        "Sincroniza el curso con POST /courses/{courseId}/sync e inténtalo de nuevo.");

app.MapPost("/courses/{courseId:int}/sync", async Task<IResult> (int courseId, SyncService sync, HttpContext ctx) =>
{
    var r = await sync.StartAsync(courseId);
    return r.Outcome switch
    {
        "accepted" => Results.Json(new SyncAcceptedDto(r.SyncId!, "running"), statusCode: 202),
        "conflict" => Problems.Result(ctx, 409, "SYNC_IN_PROGRESS", "Ya hay una sincronización en curso"),
        _ => Problems.Result(ctx, 503, "MOODLE_UNAVAILABLE", "Moodle no está disponible", r.Detail),
    };
}).RequireAuthorization();

app.MapGet("/courses/{courseId:int}/sync", async Task<IResult> (int courseId, ISyncStore store) =>
{
    var status = await store.GetStatusAsync(courseId) ?? new SyncStatusDto("never", null, null, null, null, null);
    return Results.Ok(status);
}).RequireAuthorization();

app.MapGet("/courses/{courseId:int}/students", async Task<IResult> (int courseId, int? page, int? pageSize, ISyncStore store, HttpContext ctx) =>
{
    var snapshot = await store.GetSnapshotAsync(courseId);
    if (snapshot is null) return NotSynced(ctx);
    return Results.Ok(Slice(snapshot.Students, page, pageSize));
}).RequireAuthorization();

app.MapGet("/courses/{courseId:int}/students/{studentId:int}", async Task<IResult> (int courseId, int studentId, ISyncStore store, HttpContext ctx) =>
{
    var snapshot = await store.GetSnapshotAsync(courseId);
    if (snapshot is null) return NotSynced(ctx);
    var student = snapshot.Students.FirstOrDefault(s => s.Id == studentId);
    if (student is null) return Problems.Result(ctx, 404, "STUDENT_NOT_FOUND", "El estudiante no existe en el curso");
    var grades = snapshot.Grades.Where(g => g.StudentId == studentId).ToList();
    var activities = snapshot.Progress.TryGetValue(studentId, out var p) ? p : new List<ActivityProgressDto>();
    return Results.Ok(new StudentDetailDto(student, grades, activities));
}).RequireAuthorization();

app.MapGet("/courses/{courseId:int}/grades", async Task<IResult> (int courseId, int? studentId, int? activityId, int? page, int? pageSize, ISyncStore store, HttpContext ctx) =>
{
    var snapshot = await store.GetSnapshotAsync(courseId);
    if (snapshot is null) return NotSynced(ctx);
    var grades = snapshot.Grades
        .Where(g => (studentId is null || g.StudentId == studentId) && (activityId is null || g.ActivityId == activityId))
        .OrderBy(g => g.StudentId).ThenBy(g => g.ActivityId);
    return Results.Ok(Slice(grades, page, pageSize));
}).RequireAuthorization();


app.MapGet("/health", () => Results.Ok(new { status = "ok", service = "moodle-sync" }));

app.Run();

public partial class Program { }
