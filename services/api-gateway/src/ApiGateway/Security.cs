using System.Text;
using Microsoft.IdentityModel.Tokens;

namespace ApiGateway;

// Configuración del JWT: el mismo secreto, emisor y audiencia que usa auth-courses (variables de entorno, ver .env.example).
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
public record ProblemDto(string Title, int Status, string Code, string? Detail, string TraceId);

public static class Problems
{
    public static ProblemDto Build(HttpContext ctx, int status, string code, string title, string? detail = null)
    {
        var traceId = ctx.Request.Headers["X-Request-Id"].FirstOrDefault() ?? ctx.TraceIdentifier;
        return new ProblemDto(title, status, code, detail, traceId);
    }

    public static async Task Write(HttpContext ctx, int status, string code, string title, string? detail = null)
    {
        ctx.Response.StatusCode = status;
        await ctx.Response.WriteAsJsonAsync(Build(ctx, status, code, title, detail),
            (System.Text.Json.JsonSerializerOptions?)null, "application/problem+json");
    }
}
