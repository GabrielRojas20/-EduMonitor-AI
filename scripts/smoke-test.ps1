[CmdletBinding()]
param(
    [string]$AnalyticsUrl = "http://localhost:5003",
    [string]$GatewayUrl = "http://localhost:5000",
    [string]$AuthUrl = "http://localhost:5001",
    [string]$SyncUrl = "http://localhost:5002",
    [string]$AgentUrl = "http://localhost:5004",
    [int]$CourseId = 101,
    [switch]$RequireGateway,
    [switch]$RunAgentHealth
)

$ErrorActionPreference = "Stop"
$passed = 0
$skipped = 0

function Test-Endpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Uri,
        [int[]]$ExpectedStatus = @(200),
        [switch]$Optional
    )

    try {
        $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 15
        if ($ExpectedStatus -notcontains [int]$response.StatusCode) {
            throw "HTTP $($response.StatusCode), esperado: $($ExpectedStatus -join ', ')"
        }
        Write-Host "[OK] $Name ($($response.StatusCode))" -ForegroundColor Green
        $script:passed++
        return $response
    }
    catch {
        if ($Optional) {
            Write-Host "[OMITIDO] $Name - $($_.Exception.Message)" -ForegroundColor Yellow
            $script:skipped++
            return $null
        }
        throw "[FALLO] $Name - $($_.Exception.Message)"
    }
}

Write-Host "EduMonitor AI - smoke test" -ForegroundColor Cyan
Write-Host "Analytics: $AnalyticsUrl"

Test-Endpoint "Analytics health" "$AnalyticsUrl/health" | Out-Null
Test-Endpoint "Analytics del curso $CourseId" "$AnalyticsUrl/api/v1/courses/$CourseId/analytics" | Out-Null
Test-Endpoint "Alertas del curso $CourseId" "$AnalyticsUrl/api/v1/courses/$CourseId/analytics/alerts" | Out-Null
Test-Endpoint "Reporte del curso $CourseId" "$AnalyticsUrl/api/v1/courses/$CourseId/analytics/report" | Out-Null

$gatewayHealth = Test-Endpoint "Gateway health" "$GatewayUrl/health" -Optional
$authHealth = Test-Endpoint "Auth health" "$AuthUrl/health" -Optional
$syncHealth = Test-Endpoint "Moodle Sync health" "$SyncUrl/health" -Optional

if ($RequireGateway -and $null -eq $gatewayHealth) {
    throw "El gateway era obligatorio y no respondió."
}

if ($RunAgentHealth) {
    Test-Endpoint "Agent health" "$AgentUrl/health"
}
else {
    Test-Endpoint "Agent health" "$AgentUrl/health" -Optional | Out-Null
}

Write-Host ""
Write-Host "Resultado: $passed correctos; $skipped opcionales omitidos." -ForegroundColor Cyan
if ($skipped -gt 0) {
    Write-Host "Los opcionales pueden estar pendientes hasta que se fusione la infraestructura o se inicie el agente." -ForegroundColor Yellow
}
