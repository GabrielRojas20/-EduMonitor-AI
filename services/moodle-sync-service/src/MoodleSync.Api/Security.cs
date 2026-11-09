using System.Text;
using Microsoft.IdentityModel.Tokens;

namespace MoodleSync.Api;

// El mismo secreto, emisor y audiencia que usa auth-courses (variables de entorno, ver .env.example).
public sealed class JwtSettings
{
    public string Secret { get; }
    public string Issuer { get; }
    public string Audience { get; }

    public JwtSettings(IConfiguration config)
    {
        Secret = config["JWT_SECRET"] ?? "";
        if (Encoding.UTF8.GetByteCount(Secret) < 32)
            throw new InvalidOperationException("JWT_SECRET es obligatorio y debe tener al menos 32 caracteres. Defínelo como variable de entorno (ver .env.example).");
        Issuer = config["JWT_ISSUER"] ?? "edumonitor";
        Audience = config["JWT_AUDIENCE"] ?? "edumonitor-api";
    }

    public SymmetricSecurityKey Key => new(Encoding.UTF8.GetBytes(Secret));
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
