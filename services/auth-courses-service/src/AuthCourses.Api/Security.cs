using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using Microsoft.IdentityModel.Tokens;

namespace AuthCourses.Api;

// Contraseñas con PBKDF2-SHA256, sal aleatoria y comparación en tiempo constante.
public sealed class PasswordService
{
    private const int Iterations = 210_000;
    private const int SaltSize = 16;
    private const int HashSize = 32;

    public string Hash(string password)
    {
        var salt = RandomNumberGenerator.GetBytes(SaltSize);
        var hash = Rfc2898DeriveBytes.Pbkdf2(password, salt, Iterations, HashAlgorithmName.SHA256, HashSize);
        return $"pbkdf2-sha256${Iterations}${Convert.ToBase64String(salt)}${Convert.ToBase64String(hash)}";
    }

    public bool Verify(string password, string stored)
    {
        try
        {
            var parts = stored.Split('$');
            if (parts.Length != 4 || parts[0] != "pbkdf2-sha256" || !int.TryParse(parts[1], out var iterations)) return false;
            var salt = Convert.FromBase64String(parts[2]);
            var expected = Convert.FromBase64String(parts[3]);
            var actual = Rfc2898DeriveBytes.Pbkdf2(password, salt, iterations, HashAlgorithmName.SHA256, expected.Length);
            return CryptographicOperations.FixedTimeEquals(actual, expected);
        }
        catch (FormatException)
        {
            return false;
        }
    }
}

// Configuración del JWT. Todo viene de variables de entorno (ver .env.example).
public sealed class JwtSettings
{
    public string Secret { get; }
    public string Issuer { get; }
    public string Audience { get; }
    public int ExpiresMinutes { get; }

    public JwtSettings(IConfiguration config)
    {
        Secret = config["JWT_SECRET"] ?? "";
        if (Encoding.UTF8.GetByteCount(Secret) < 32)
            throw new InvalidOperationException("JWT_SECRET es obligatorio y debe tener al menos 32 caracteres. Defínelo como variable de entorno (ver .env.example).");
        Issuer = config["JWT_ISSUER"] ?? "edumonitor";
        Audience = config["JWT_AUDIENCE"] ?? "edumonitor-api";
        ExpiresMinutes = int.TryParse(config["JWT_EXPIRES_MINUTES"], out var m) && m > 0 ? m : 60;
    }

    public SymmetricSecurityKey Key => new(Encoding.UTF8.GetBytes(Secret));
}

public sealed class TokenService(JwtSettings settings)
{
    // Claims: sub (id), role, name, email, jti; más iss, aud, iat y exp.
    public (string Token, int ExpiresInSeconds) Create(AppUser user)
    {
        var now = DateTime.UtcNow;
        var claims = new List<Claim>
        {
            new(JwtRegisteredClaimNames.Sub, user.Id.ToString()),
            new("role", user.Role),
            new("name", user.Name),
            new(JwtRegisteredClaimNames.Email, user.Email),
            new(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
        };
        var jwt = new JwtSecurityToken(
            issuer: settings.Issuer,
            audience: settings.Audience,
            claims: claims,
            notBefore: now,
            expires: now.AddMinutes(settings.ExpiresMinutes),
            signingCredentials: new SigningCredentials(settings.Key, SecurityAlgorithms.HmacSha256));
        return (new JwtSecurityTokenHandler().WriteToken(jwt), settings.ExpiresMinutes * 60);
    }
}

// Errores con el formato Problem del contrato (RFC 7807).
public static class Problems
{
    public static ProblemDto Build(HttpContext ctx, int status, string code, string title, string? detail = null)
    {
        var traceId = ctx.Request.Headers["X-Request-Id"].FirstOrDefault() ?? ctx.TraceIdentifier;
        return new ProblemDto(title, status, code, detail, traceId);
    }

    public static IResult Result(HttpContext ctx, int status, string code, string title, string? detail = null)
        => Results.Json(Build(ctx, status, code, title, detail), contentType: "application/problem+json", statusCode: status);
}
