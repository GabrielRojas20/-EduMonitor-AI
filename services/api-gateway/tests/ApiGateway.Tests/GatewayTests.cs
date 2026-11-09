using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.IdentityModel.Tokens;
using Xunit;

namespace ApiGateway.Tests;

// Levanta servicios falsos (auth-courses, moodle-sync y analytics) en puertos libres y el gateway real delante.
// Claves y datos SOLO para pruebas (ficticios).
public sealed class GatewayFactory : WebApplicationFactory<Program>
{
    public const string Secret = "clave-de-prueba-solo-para-tests-0123456789";

    public int SyncCalls;
    private readonly WebApplication _auth;
    private readonly WebApplication _sync;
    private readonly WebApplication _analytics;

    public GatewayFactory()
    {
        _auth = Start(app =>
        {
            app.MapGet("/internal/courses/{id:int}/access", IResult (int id, HttpRequest req) =>
            {
                if (!req.Headers.ContainsKey("Authorization")) return Results.StatusCode(401);
                if (id == 2) return Results.NoContent();
                if (id == 999) return Results.NotFound();
                return Results.StatusCode(403);
            });
            app.MapPost("/auth/login", () => Results.Json(new { accessToken = "token-falso", tokenType = "Bearer" }));
            app.MapGet("/courses", () => Results.Json(new[] { new { id = 2, shortName = "PRUEBA01" } }));
        });

        _sync = Start(app =>
        {
            app.MapGet("/courses/{id:int}/students", (int id, HttpRequest req) =>
            {
                Interlocked.Increment(ref SyncCalls);
                return Results.Json(new
                {
                    items = Array.Empty<object>(),
                    page = 1,
                    pageSize = 50,
                    total = 0,
                    receivedAuthorization = req.Headers.Authorization.ToString(),
                    receivedRequestId = req.Headers["X-Request-Id"].ToString(),
                });
            });
        });

        _analytics = Start(app =>
        {
            // analytics conserva el prefijo /api/v1 (el gateway no lo quita)
            app.MapGet("/api/v1/courses/{id:int}/analytics", (int id) => Results.Json(new { courseId = id }));
        });
    }

    private static WebApplication Start(Action<WebApplication> map)
    {
        var b = WebApplication.CreateBuilder();
        b.WebHost.UseUrls("http://127.0.0.1:0");
        b.Logging.ClearProviders();
        var app = b.Build();
        map(app);
        app.StartAsync().GetAwaiter().GetResult();
        return app;
    }

    private static string Url(WebApplication app) => app.Urls.First().TrimEnd('/') + "/";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureAppConfiguration((_, cfg) => cfg.AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["JWT_SECRET"] = Secret,
            ["JWT_ISSUER"] = "edumonitor",
            ["JWT_AUDIENCE"] = "edumonitor-api",
            ["ReverseProxy:Clusters:auth:Destinations:d1:Address"] = Url(_auth),
            ["ReverseProxy:Clusters:sync:Destinations:d1:Address"] = Url(_sync),
            ["ReverseProxy:Clusters:analytics:Destinations:d1:Address"] = Url(_analytics),
        }));
    }

    protected override void Dispose(bool disposing)
    {
        base.Dispose(disposing);
        if (!disposing) return;
        _auth.StopAsync().GetAwaiter().GetResult();
        _sync.StopAsync().GetAwaiter().GetResult();
        _analytics.StopAsync().GetAwaiter().GetResult();
    }
}

public class GatewayTests : IClassFixture<GatewayFactory>
{
    private readonly GatewayFactory _factory;
    private readonly HttpClient _http;

    public GatewayTests(GatewayFactory factory)
    {
        _factory = factory;
        _http = factory.CreateClient();
    }

    private static string MakeToken(string secret, DateTime notBefore, DateTime expires)
    {
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret));
        var claims = new[] { new Claim("sub", "1"), new Claim("role", "teacher") };
        var jwt = new JwtSecurityToken("edumonitor", "edumonitor-api", claims, notBefore, expires,
            new SigningCredentials(key, SecurityAlgorithms.HmacSha256));
        return new JwtSecurityTokenHandler().WriteToken(jwt);
    }

    private static string ValidToken() => MakeToken(GatewayFactory.Secret, DateTime.UtcNow, DateTime.UtcNow.AddHours(1));

    private async Task<HttpResponseMessage> GetAsync(string url, string? token, string? requestId = null, HttpClient? client = null)
    {
        var msg = new HttpRequestMessage(HttpMethod.Get, url);
        if (token is not null) msg.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        if (requestId is not null) msg.Headers.Add("X-Request-Id", requestId);
        return await (client ?? _http).SendAsync(msg);
    }

    private static async Task AssertProblem(HttpResponseMessage r, HttpStatusCode status, string code)
    {
        Assert.Equal(status, r.StatusCode);
        Assert.Equal("application/problem+json", r.Content.Headers.ContentType?.MediaType);
        var body = await r.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal(code, body.GetProperty("code").GetString());
    }

    [Fact]
    public async Task Sin_token_devuelve_401()
    {
        await AssertProblem(await GetAsync("/api/v1/courses", null), HttpStatusCode.Unauthorized, "TOKEN_INVALID");
    }

    [Fact]
    public async Task Token_vencido_devuelve_401_TOKEN_EXPIRED()
    {
        var token = MakeToken(GatewayFactory.Secret, DateTime.UtcNow.AddHours(-2), DateTime.UtcNow.AddHours(-1));
        await AssertProblem(await GetAsync("/api/v1/courses", token), HttpStatusCode.Unauthorized, "TOKEN_EXPIRED");
    }

    [Fact]
    public async Task Token_con_firma_ajena_devuelve_401_TOKEN_INVALID()
    {
        var token = MakeToken("otra-clave-distinta-con-mas-de-32-caracteres", DateTime.UtcNow, DateTime.UtcNow.AddHours(1));
        await AssertProblem(await GetAsync("/api/v1/courses", token), HttpStatusCode.Unauthorized, "TOKEN_INVALID");
    }

    [Fact]
    public async Task Login_no_exige_token_y_llega_a_auth_courses()
    {
        var r = await _http.PostAsJsonAsync("/api/v1/auth/login", new { email = "a@b.test", password = "x" });
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
        var body = await r.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal("token-falso", body.GetProperty("accessToken").GetString());
    }

    [Fact]
    public async Task Lista_de_cursos_con_token_valido_devuelve_200()
    {
        var r = await GetAsync("/api/v1/courses", ValidToken());
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
    }

    [Fact]
    public async Task Curso_propio_llega_a_moodle_sync()
    {
        var r = await GetAsync("/api/v1/courses/2/students", ValidToken());
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
    }

    [Fact]
    public async Task Curso_de_otro_docente_devuelve_403_y_no_llega_al_servicio()
    {
        var antes = _factory.SyncCalls;
        var r = await GetAsync("/api/v1/courses/3/students", ValidToken());
        await AssertProblem(r, HttpStatusCode.Forbidden, "COURSE_NOT_AUTHORIZED");
        Assert.Equal(antes, _factory.SyncCalls);
    }

    [Fact]
    public async Task Curso_inexistente_devuelve_404()
    {
        var r = await GetAsync("/api/v1/courses/999/students", ValidToken());
        await AssertProblem(r, HttpStatusCode.NotFound, "COURSE_NOT_FOUND");
    }

    [Fact]
    public async Task Analytics_conserva_el_prefijo_api_v1()
    {
        var r = await GetAsync("/api/v1/courses/2/analytics", ValidToken());
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
        var body = await r.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal(2, body.GetProperty("courseId").GetInt32());
    }

    [Fact]
    public async Task Reenvia_el_token_y_el_id_de_la_peticion()
    {
        var token = ValidToken();
        var r = await GetAsync("/api/v1/courses/2/students", token, requestId: "prueba-123");
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
        Assert.Equal("prueba-123", r.Headers.GetValues("X-Request-Id").Single());
        var body = await r.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal("Bearer " + token, body.GetProperty("receivedAuthorization").GetString());
        Assert.Equal("prueba-123", body.GetProperty("receivedRequestId").GetString());
    }

    [Fact]
    public async Task Las_rutas_internas_no_se_publican()
    {
        var r = await GetAsync("/internal/courses/2/access", ValidToken());
        Assert.Equal(HttpStatusCode.NotFound, r.StatusCode);
    }

    [Fact]
    public async Task Cors_permite_solo_el_origen_del_front()
    {
        var ok = new HttpRequestMessage(HttpMethod.Options, "/api/v1/courses");
        ok.Headers.Add("Origin", "http://localhost:5173");
        ok.Headers.Add("Access-Control-Request-Method", "GET");
        ok.Headers.Add("Access-Control-Request-Headers", "authorization");
        var r1 = await _http.SendAsync(ok);
        Assert.True(r1.Headers.Contains("Access-Control-Allow-Origin"));

        var ajeno = new HttpRequestMessage(HttpMethod.Options, "/api/v1/courses");
        ajeno.Headers.Add("Origin", "http://sitio-ajeno.test");
        ajeno.Headers.Add("Access-Control-Request-Method", "GET");
        var r2 = await _http.SendAsync(ajeno);
        Assert.False(r2.Headers.Contains("Access-Control-Allow-Origin"));
    }

    [Fact]
    public async Task Servicio_caido_devuelve_503_con_formato_Problem()
    {
        var caido = _factory.WithWebHostBuilder(b => b.ConfigureAppConfiguration((_, cfg) =>
            cfg.AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["ReverseProxy:Clusters:analytics:Destinations:d1:Address"] = "http://127.0.0.1:1/",
            })));
        var r = await GetAsync("/api/v1/courses/2/analytics", ValidToken(), client: caido.CreateClient());
        await AssertProblem(r, HttpStatusCode.ServiceUnavailable, "MOODLE_UNAVAILABLE");
    }
}
