using System.IdentityModel.Tokens.Jwt;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.IdentityModel.Tokens;
using Xunit;

namespace MoodleSync.Tests;

// Claves y datos SOLO para pruebas (ficticios).
public sealed class MoodleSyncFactory(string moodleUrl) : WebApplicationFactory<Program>
{
    public const string Secret = "clave-de-prueba-solo-para-tests-0123456789";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureAppConfiguration((_, cfg) => cfg.AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["JWT_SECRET"] = Secret,
            ["JWT_ISSUER"] = "edumonitor",
            ["JWT_AUDIENCE"] = "edumonitor-api",
            ["MOODLE_BASE_URL"] = moodleUrl,
            ["MOODLE_WS_TOKEN"] = FakeMoodle.Token,
        }));
    }
}

// Cada prueba crea su propio Moodle falso y su propio servicio: así no comparten estado.
public sealed class TestEnv : IDisposable
{
    public FakeMoodle Moodle { get; } = new();
    public HttpClient Http { get; }
    private readonly MoodleSyncFactory _factory;

    public TestEnv(string? moodleUrlOverride = null)
    {
        _factory = new MoodleSyncFactory(moodleUrlOverride ?? Moodle.Url);
        Http = _factory.CreateClient();
        Http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", MakeToken(Secret, DateTime.UtcNow, DateTime.UtcNow.AddHours(1)));
    }

    public static string Secret => MoodleSyncFactory.Secret;

    // Cliente sin el encabezado Authorization.
    public HttpClient Anonymous() => _factory.CreateClient();

    public static string MakeToken(string secret, DateTime notBefore, DateTime expires)
    {
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret));
        var claims = new[] { new Claim("sub", "1"), new Claim("role", "teacher") };
        var jwt = new JwtSecurityToken("edumonitor", "edumonitor-api", claims, notBefore, expires,
            new SigningCredentials(key, SecurityAlgorithms.HmacSha256));
        return new JwtSecurityTokenHandler().WriteToken(jwt);
    }

    public async Task<JsonElement> JsonAsync(string url)
    {
        var r = await Http.GetAsync(url);
        return await r.Content.ReadFromJsonAsync<JsonElement>();
    }

    // Inicia la sincronización y espera a que deje de estar "running". Devuelve el estado final.
    public async Task<JsonElement> SyncAndWaitAsync(int courseId)
    {
        var post = await Http.PostAsync($"/courses/{courseId}/sync", null);
        Assert.Equal(System.Net.HttpStatusCode.Accepted, post.StatusCode);
        for (var i = 0; i < 100; i++)
        {
            var status = await JsonAsync($"/courses/{courseId}/sync");
            if (status.GetProperty("state").GetString() != "running") return status;
            await Task.Delay(100);
        }
        throw new TimeoutException("La sincronización no terminó a tiempo.");
    }

    public void Dispose()
    {
        Http.Dispose();
        _factory.Dispose();
        Moodle.Dispose();
    }
}
