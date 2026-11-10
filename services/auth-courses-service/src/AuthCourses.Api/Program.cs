using System.Security.Claims;
using System.Text.Json;
using System.Text.Json.Serialization;
using AuthCourses.Api;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

builder.Services.ConfigureHttpJsonOptions(o => o.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull);

builder.Services.AddSingleton<PasswordService>();
builder.Services.AddSingleton(sp => new JwtSettings(sp.GetRequiredService<IConfiguration>()));
builder.Services.AddSingleton<TokenService>();

// Sin cadena de conexión usa una base en memoria (desarrollo y pruebas).
// Con ConnectionStrings__Auth usa SQL Server (esquema auth, ver database/migrations).
builder.Services.AddDbContext<AuthDb>((sp, o) =>
{
    var cs = sp.GetRequiredService<IConfiguration>().GetConnectionString("Auth");
    if (string.IsNullOrWhiteSpace(cs)) o.UseInMemoryDatabase("auth");
    else o.UseSqlServer(cs);
});

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
            // 401 con el formato Problem: TOKEN_EXPIRED si venció; TOKEN_INVALID si falta o no es válido.
            OnChallenge = async c =>
            {
                c.HandleResponse();
                var expired = c.AuthenticateFailure is SecurityTokenExpiredException;
                var problem = Problems.Build(c.HttpContext, 401,
                    expired ? "TOKEN_EXPIRED" : "TOKEN_INVALID",
                    expired ? "El token venció" : "Token ausente o inválido");
                c.Response.StatusCode = 401;
                await c.Response.WriteAsJsonAsync(problem, (JsonSerializerOptions?)null, "application/problem+json");
            },
        };
    });
builder.Services.AddAuthorization();

var app = builder.Build();

app.Services.GetRequiredService<JwtSettings>(); // falla al arrancar si falta JWT_SECRET

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AuthDb>();
    if (db.Database.IsInMemory()) db.Database.EnsureCreated();
    var seedPassword = app.Configuration["AUTH_SEED_PASSWORD"];
    if (!string.IsNullOrEmpty(seedPassword))
        Seed.Run(db, scope.ServiceProvider.GetRequiredService<PasswordService>(), seedPassword);
}

app.UseAuthentication();
app.UseAuthorization();

var passwords = app.Services.GetRequiredService<PasswordService>();
var dummyHash = passwords.Hash("clave-de-relleno"); // para no revelar por tiempo si el correo existe

static int? UserId(ClaimsPrincipal p) => int.TryParse(p.FindFirst("sub")?.Value, out var id) ? id : null;
static UserDto UserToDto(AppUser u) => new(u.Id, u.Name, u.Email, u.Role);
static CourseDto CourseToDto(CourseEntity c) => new(c.Id, c.ShortName, c.FullName, null, null);

// null = acceso permitido; si no, la respuesta de error que corresponde.
static async Task<IResult?> CheckAccess(HttpContext ctx, ClaimsPrincipal p, AuthDb db, int courseId)
{
    if (UserId(p) is not int uid) return Problems.Result(ctx, 401, "TOKEN_INVALID", "Token inválido");
    if (!await db.Courses.AnyAsync(c => c.Id == courseId))
        return Problems.Result(ctx, 404, "COURSE_NOT_FOUND", "El curso no existe");
    var allowed = await db.TeacherCourses.AnyAsync(t => t.UserId == uid && t.CourseId == courseId);
    return allowed ? null : Problems.Result(ctx, 403, "COURSE_NOT_AUTHORIZED", "El usuario no tiene acceso a ese curso");
}

app.MapPost("/auth/login", async Task<IResult> (LoginRequest req, AuthDb db, TokenService tokens, HttpContext ctx) =>
{
    var email = (req.Email ?? "").Trim().ToLowerInvariant();
    var user = string.IsNullOrEmpty(email) ? null : await db.Users.FirstOrDefaultAsync(u => u.Email == email);
    var ok = passwords.Verify(req.Password ?? "", user?.PasswordHash ?? dummyHash);
    if (user is null || !ok)
        return Problems.Result(ctx, 401, "INVALID_CREDENTIALS", "Credenciales inválidas");
    var (token, expiresIn) = tokens.Create(user);
    return Results.Ok(new LoginResponse(token, "Bearer", expiresIn, UserToDto(user)));
});

app.MapGet("/users/me", async Task<IResult> (ClaimsPrincipal p, AuthDb db, HttpContext ctx) =>
{
    if (UserId(p) is not int uid) return Problems.Result(ctx, 401, "TOKEN_INVALID", "Token inválido");
    var user = await db.Users.FindAsync(uid);
    if (user is null) return Problems.Result(ctx, 401, "TOKEN_INVALID", "Token inválido");
    return Results.Ok(UserToDto(user));
}).RequireAuthorization();

app.MapGet("/courses", async Task<IResult> (ClaimsPrincipal p, AuthDb db, HttpContext ctx) =>
{
    if (UserId(p) is not int uid) return Problems.Result(ctx, 401, "TOKEN_INVALID", "Token inválido");
    var ids = await db.TeacherCourses.Where(t => t.UserId == uid).Select(t => t.CourseId).ToListAsync();
    var courses = await db.Courses.Where(c => ids.Contains(c.Id)).OrderBy(c => c.ShortName).ToListAsync();
    return Results.Ok(courses.Select(c => CourseToDto(c)).ToList());
}).RequireAuthorization();

app.MapGet("/courses/{courseId:int}", async Task<IResult> (int courseId, HttpContext ctx, ClaimsPrincipal p, AuthDb db) =>
{
    var denied = await CheckAccess(ctx, p, db, courseId);
    if (denied is not null) return denied;
    var course = await db.Courses.FindAsync(courseId);
    return Results.Ok(CourseToDto(course!));
}).RequireAuthorization();

// Lo llama el gateway antes de enrutar cualquier /courses/{courseId}/...
app.MapGet("/internal/courses/{courseId:int}/access", async Task<IResult> (int courseId, HttpContext ctx, ClaimsPrincipal p, AuthDb db) =>
{
    var denied = await CheckAccess(ctx, p, db, courseId);
    return denied ?? Results.NoContent();
}).RequireAuthorization();


app.MapGet("/health", () => Results.Ok(new { status = "ok", service = "auth-courses" }));

app.Run();

public partial class Program { }
