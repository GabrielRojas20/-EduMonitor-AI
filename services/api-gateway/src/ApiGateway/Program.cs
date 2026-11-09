using System.Net;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using ApiGateway;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Cors.Infrastructure;
using Microsoft.IdentityModel.Tokens;
using Yarp.ReverseProxy.Forwarder;

var builder = WebApplication.CreateBuilder(args);

builder.Services.ConfigureHttpJsonOptions(o => o.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull);
builder.Services.AddSingleton(sp => new JwtSettings(sp.GetRequiredService<IConfiguration>()));

// Validación del JWT: firma, vencimiento, emisor y audiencia.
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
                await Problems.Write(c.HttpContext, 401,
                    expired ? "TOKEN_EXPIRED" : "TOKEN_INVALID",
                    expired ? "El token venció" : "Token ausente o inválido");
            },
        };
    });
builder.Services.AddAuthorization();

// CORS: solo el origen del front (CORS_ALLOWED_ORIGINS, separados por coma).
builder.Services.AddCors();
builder.Services.AddOptions<CorsOptions>().Configure<IConfiguration>((o, cfg) =>
{
    var origins = (cfg["CORS_ALLOWED_ORIGINS"] ?? "http://localhost:5173")
        .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
    o.AddPolicy("front", p => p.WithOrigins(origins).AllowAnyMethod().WithHeaders("Authorization", "Content-Type", "X-Request-Id"));
});

// Cliente para la llamada previa de autorización a auth-courses (misma dirección que el cluster "auth").
builder.Services.AddHttpClient("auth", (sp, c) =>
{
    var address = sp.GetRequiredService<IConfiguration>()["ReverseProxy:Clusters:auth:Destinations:d1:Address"] ?? "http://localhost:5001/";
    c.BaseAddress = new Uri(address);
    c.Timeout = TimeSpan.FromSeconds(5);
});

builder.Services.AddReverseProxy().LoadFromConfig(builder.Configuration.GetSection("ReverseProxy"));

var app = builder.Build();

app.Services.GetRequiredService<JwtSettings>(); // falla al arrancar si falta JWT_SECRET

// X-Request-Id: se genera si no llega, se reenvía a los servicios y se devuelve en la respuesta.
app.Use(async (ctx, next) =>
{
    var id = ctx.Request.Headers["X-Request-Id"].FirstOrDefault();
    if (string.IsNullOrWhiteSpace(id))
    {
        id = Guid.NewGuid().ToString("N");
        ctx.Request.Headers["X-Request-Id"] = id;
    }
    ctx.Response.OnStarting(() =>
    {
        ctx.Response.Headers["X-Request-Id"] = id;
        return Task.CompletedTask;
    });
    await next();
});

app.UseCors("front");
app.UseAuthentication();
app.UseAuthorization();

// Si un servicio interno no responde: 503 con el formato Problem (y no un 502 vacío).
app.Use(async (ctx, next) =>
{
    await next();
    if (ctx.Features.Get<IForwarderErrorFeature>() is not null && !ctx.Response.HasStarted)
        await Problems.Write(ctx, 503, "MOODLE_UNAVAILABLE", "Un servicio interno no responde");
});

// Llamada previa a auth-courses antes de enrutar cualquier /api/v1/courses/{courseId}/...
var courseRoute = new Regex(@"^/api/v1/courses/(\d+)(/|$)", RegexOptions.Compiled);
app.Use(async (ctx, next) =>
{
    var match = courseRoute.Match(ctx.Request.Path.Value ?? "");
    if (!match.Success || HttpMethods.IsOptions(ctx.Request.Method))
    {
        await next();
        return;
    }

    var request = new HttpRequestMessage(HttpMethod.Get, $"/internal/courses/{match.Groups[1].Value}/access");
    if (AuthenticationHeaderValue.TryParse(ctx.Request.Headers.Authorization.ToString(), out var auth))
        request.Headers.Authorization = auth; // se reenvía el JWT del docente
    request.Headers.TryAddWithoutValidation("X-Request-Id", ctx.Request.Headers["X-Request-Id"].ToString());

    HttpStatusCode status;
    try
    {
        var client = ctx.RequestServices.GetRequiredService<IHttpClientFactory>().CreateClient("auth");
        using var response = await client.SendAsync(request, ctx.RequestAborted);
        status = response.StatusCode;
    }
    catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException)
    {
        await Problems.Write(ctx, 503, "MOODLE_UNAVAILABLE", "Un servicio interno no responde");
        return;
    }

    if (status == HttpStatusCode.NoContent) { await next(); return; }
    if (status == HttpStatusCode.Forbidden) { await Problems.Write(ctx, 403, "COURSE_NOT_AUTHORIZED", "El usuario no tiene acceso a ese curso"); return; }
    if (status == HttpStatusCode.NotFound) { await Problems.Write(ctx, 404, "COURSE_NOT_FOUND", "El curso no existe"); return; }
    if (status == HttpStatusCode.Unauthorized) { await Problems.Write(ctx, 401, "TOKEN_INVALID", "Token inválido"); return; }
    await Problems.Write(ctx, 503, "MOODLE_UNAVAILABLE", "Un servicio interno no responde");
});

app.MapReverseProxy();

app.Run();

public partial class Program { }
