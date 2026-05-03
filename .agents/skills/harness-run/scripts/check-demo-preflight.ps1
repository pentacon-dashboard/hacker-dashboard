[CmdletBinding()]
param(
    [string]$ApiBase = "",
    [string]$AppBase = "",
    [string[]]$RequiredClients = @("client-001", "client-002", "client-003"),
    [int]$MinHoldings = 1,
    [switch]$SkipFrontend
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ApiBase)) {
    $ApiBase = $env:HARNESS_API_BASE
}
if ([string]::IsNullOrWhiteSpace($ApiBase)) {
    $ApiBase = "http://127.0.0.1:8000"
}
if ([string]::IsNullOrWhiteSpace($AppBase)) {
    $AppBase = $env:HARNESS_APP_BASE
}
if ([string]::IsNullOrWhiteSpace($AppBase)) {
    $AppBase = "http://127.0.0.1:3000"
}

$ApiBase = $ApiBase.TrimEnd("/")
$AppBase = $AppBase.TrimEnd("/")
$failures = New-Object System.Collections.Generic.List[string]

function Add-Failure {
    param([string]$Message)
    $failures.Add($Message) | Out-Null
}

function Get-ApiJson {
    param([string]$Path)

    $uri = "$ApiBase$Path"
    try {
        return Invoke-RestMethod -Uri $uri -TimeoutSec 10
    } catch {
        Add-Failure "GET $uri failed: $($_.Exception.Message)"
        return $null
    }
}

Write-Host "[demo-preflight] API base: $ApiBase"
if (-not $SkipFrontend) {
    Write-Host "[demo-preflight] App base: $AppBase"
}

$health = Get-ApiJson "/health"
if ($null -ne $health) {
    $dbStatus = $null
    if ($null -ne $health.services -and $health.services.PSObject.Properties.Name -contains "db") {
        $dbStatus = [string]$health.services.db
    }
    if ($dbStatus -ne "ok") {
        Add-Failure "/health did not report services.db=ok (actual: $dbStatus)"
    }
}

$clientsResponse = Get-ApiJson "/portfolio/clients"
$clientIds = @()
if ($null -ne $clientsResponse -and $null -ne $clientsResponse.clients) {
    $clientIds = @($clientsResponse.clients | ForEach-Object { [string]$_.client_id })
    Write-Host "[demo-preflight] Clients: $($clientIds -join ', ')"
} else {
    Add-Failure "/portfolio/clients returned no clients array"
}

foreach ($clientId in $RequiredClients) {
    if ($clientIds -notcontains $clientId) {
        Add-Failure "Required client '$clientId' is missing from /portfolio/clients"
        continue
    }

    $encodedClientId = [System.Uri]::EscapeDataString($clientId)
    $summary = Get-ApiJson "/portfolio/summary?client_id=$encodedClientId"
    if ($null -eq $summary) {
        continue
    }

    $holdingsCount = 0
    if ($summary.PSObject.Properties.Name -contains "holdings_count") {
        $holdingsCount = [int]$summary.holdings_count
    }
    if ($holdingsCount -lt $MinHoldings) {
        Add-Failure "Client '$clientId' has holdings_count=$holdingsCount; expected >= $MinHoldings"
    }

    $totalValue = [decimal]0
    if ($summary.PSObject.Properties.Name -contains "total_value_krw") {
        [void][decimal]::TryParse([string]$summary.total_value_krw, [ref]$totalValue)
    }
    if ($totalValue -le 0) {
        Add-Failure "Client '$clientId' has total_value_krw=$totalValue; expected > 0"
    }
}

if (-not $SkipFrontend) {
    try {
        $response = Invoke-WebRequest -Uri $AppBase -UseBasicParsing -TimeoutSec 10
        if ([int]$response.StatusCode -lt 200 -or [int]$response.StatusCode -ge 400) {
            Add-Failure "Frontend $AppBase returned HTTP $($response.StatusCode)"
        }
    } catch {
        Add-Failure "Frontend $AppBase failed: $($_.Exception.Message)"
    }
}

if ($failures.Count -gt 0) {
    Write-Host "[demo-preflight] FAIL" -ForegroundColor Red
    foreach ($failure in $failures) {
        Write-Host " - $failure" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Remediation hints:"
    Write-Host " - Verify Docker Postgres is running and the backend DATABASE_URL points at that instance."
    Write-Host " - Run backend migrations against the same database used by the running backend."
    Write-Host " - Seed or upload demo holdings for every linked demo client before browser smoke."
    Write-Host " - Do not accept a browser smoke while client pages remain in skeleton, empty, or hidden-error states."
    exit 1
}

Write-Host "[demo-preflight] PASS"
Write-Host "[demo-preflight] Required clients have live holdings and the demo app is reachable."
