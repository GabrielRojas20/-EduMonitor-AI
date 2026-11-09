using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.IdentityModel.Tokens;
using Xunit;

namespace AuthCourses.Tests;

// Claves y contraseñas SOLO para pruebas (datos ficticios).
public class AuthFactory : WebApplicationFactory<Program>
{
    public const string Secret = "clave-de-prueba-solo-para-tests-0123456789";
    public const string Password = "Prueba-Tests-2026";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseSetting("JWT_SECRET", Secret);
        builder.UseSetting("JWT_ISSUER", "edumonitor");
        builder.UseSetting("JWT_AUDIENCE", "edumonitor-api");
        builder.UseSetting("AUTH_SEED_PASSWORD", Password);
    }
}

public class AuthTests : IClassFixture<AuthFactory>
{
    private readonly HttpClient _http;

    public AuthTests(AuthFactory factory) => _http = factory.CreateClient();

    private async Task<string> LoginAsync(string email)
    {
        var r = await _http.PostAsJsonAsync("/auth/login", new { email, password = AuthFactory.Password });
        r.EnsureSuccessStatusCode();
        var body = await r.Content.ReadFromJsonAsync<JsonElement>();
        return body.GetProperty("accessToken").GetString()!;
    }

    private async Task<HttpResponseMessage> GetAsync(string url, string? token)
    {
        var msg = new HttpRequestMessage(HttpMethod.Get, url);
        if (token is not null) msg.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        return await _http.SendAsync(msg);
    }

    private static string MakeToken(string secret, DateTime notBefore, DateTime expires)
    {
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret));
        var claims = new[] { new Claim("sub", "1"), new Claim("role", "teacher") };
        var jwt = new JwtSecurityToken("edumonitor", "edumonitor-api", claims, notBefore, expires,
            new SigningCredentials(key, SecurityAlgorithms.HmacSha256));
        return new JwtSecurityTokenHandler().WriteToken(jwt);
    }

    private static async Task AssertProblem(HttpResponseMessage r, HttpStatusCode status, string code)
    {
        Assert.Equal(status, r.StatusCode);
        Assert.Equal("application/problem+json", r.Content.Headers.ContentType?.MediaType);
        var body = await r.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal(code, body.GetProperty("code").GetString());
    }

    [Fact]
    public async Task Login_valido_devuelve_un_jwt()
    {
        var r = await _http.PostAsJsonAsync("/auth/login", new { email = "docente1@edumonitor.test", password = AuthFactory.Password });
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
        var body = await r.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal("Bearer", body.GetProperty("tokenType").GetString());
        Assert.Equal(3600, body.GetProperty("expiresIn").GetInt32());
        Assert.Equal("teacher", body.GetProperty("user").GetProperty("role").GetString());
        Assert.False(string.IsNullOrWhiteSpace(body.GetProperty("accessToken").GetString()));
    }

    [Fact]
    public async Task Login_con_clave_incorrecta_devuelve_401()
    {
        var r = await _http.PostAsJsonAsync("/auth/login", new { email = "docente1@edumonitor.test", password = "otra-clave" });
        await AssertProblem(r, HttpStatusCode.Unauthorized, "INVALID_CREDENTIALS");
    }

    [Fact]
    public async Task Login_con_usuario_inexistente_devuelve_401()
    {
        var r = await _http.PostAsJsonAsync("/auth/login", new { email = "nadie@edumonitor.test", password = AuthFactory.Password });
        await AssertProblem(r, HttpStatusCode.Unauthorized, "INVALID_CREDENTIALS");
    }

    [Fact]
    public async Task Sin_token_devuelve_401()
    {
        var r = await GetAsync("/courses", null);
        await AssertProblem(r, HttpStatusCode.Unauthorized, "TOKEN_INVALID");
    }

    [Fact]
    public async Task Token_vencido_devuelve_401_TOKEN_EXPIRED()
    {
        var token = MakeToken(AuthFactory.Secret, DateTime.UtcNow.AddHours(-2), DateTime.UtcNow.AddHours(-1));
        var r = await GetAsync("/courses", token);
        await AssertProblem(r, HttpStatusCode.Unauthorized, "TOKEN_EXPIRED");
    }

    [Fact]
    public async Task Token_con_firma_ajena_devuelve_401_TOKEN_INVALID()
    {
        var token = MakeToken("otra-clave-distinta-con-mas-de-32-caracteres", DateTime.UtcNow, DateTime.UtcNow.AddHours(1));
        var r = await GetAsync("/courses", token);
        await AssertProblem(r, HttpStatusCode.Unauthorized, "TOKEN_INVALID");
    }

    [Fact]
    public async Task Me_devuelve_el_usuario_del_token()
    {
        var token = await LoginAsync("docente1@edumonitor.test");
        var r = await GetAsync("/users/me", token);
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
        var body = await r.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal("docente1@edumonitor.test", body.GetProperty("email").GetString());
    }

    [Fact]
    public async Task Cada_docente_ve_solo_sus_cursos()
    {
        var t1 = await LoginAsync("docente1@edumonitor.test");
        var t2 = await LoginAsync("docente2@edumonitor.test");

        var c1 = await (await GetAsync("/courses", t1)).Content.ReadFromJsonAsync<JsonElement>();
        var c2 = await (await GetAsync("/courses", t2)).Content.ReadFromJsonAsync<JsonElement>();

        Assert.Equal(new[] { 2 }, c1.EnumerateArray().Select(x => x.GetProperty("id").GetInt32()).ToArray());
        Assert.Equal(new[] { 3 }, c2.EnumerateArray().Select(x => x.GetProperty("id").GetInt32()).ToArray());
    }

    [Fact]
    public async Task Curso_propio_devuelve_200()
    {
        var token = await LoginAsync("docente1@edumonitor.test");
        var r = await GetAsync("/courses/2", token);
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
    }

    [Fact]
    public async Task Curso_de_otro_docente_devuelve_403()
    {
        var token = await LoginAsync("docente1@edumonitor.test");
        var r = await GetAsync("/courses/3", token);
        await AssertProblem(r, HttpStatusCode.Forbidden, "COURSE_NOT_AUTHORIZED");
    }

    [Fact]
    public async Task Curso_inexistente_devuelve_404()
    {
        var token = await LoginAsync("docente1@edumonitor.test");
        var r = await GetAsync("/courses/999", token);
        await AssertProblem(r, HttpStatusCode.NotFound, "COURSE_NOT_FOUND");
    }

    [Fact]
    public async Task Acceso_interno_responde_204_o_403()
    {
        var token = await LoginAsync("docente1@edumonitor.test");
        var propio = await GetAsync("/internal/courses/2/access", token);
        var ajeno = await GetAsync("/internal/courses/3/access", token);
        Assert.Equal(HttpStatusCode.NoContent, propio.StatusCode);
        await AssertProblem(ajeno, HttpStatusCode.Forbidden, "COURSE_NOT_AUTHORIZED");
    }

    [Fact]
    public async Task El_administrador_no_ve_cursos_que_no_tiene_autorizados()
    {
        var token = await LoginAsync("admin@edumonitor.test");
        var r = await GetAsync("/courses", token);
        var body = await r.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Empty(body.EnumerateArray());
        await AssertProblem(await GetAsync("/courses/2", token), HttpStatusCode.Forbidden, "COURSE_NOT_AUTHORIZED");
    }
}
