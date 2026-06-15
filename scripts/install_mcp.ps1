# Install Splunk MCP Server (Splunkbase app 7931)
# https://splunkbase.splunk.com/app/7931

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $Root ".env"
$PackagesDir = Join-Path $Root "packages"

if (-not (Test-Path $EnvFile)) {
    Write-Host "Copy .env.example to .env and set Splunk credentials first." -ForegroundColor Red
    exit 1
}

$vars = @{}
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match "^([^#=]+)=(.*)$") { $vars[$matches[1].Trim()] = $matches[2].Trim() }
}

$SplunkBin = "C:\Program Files\Splunk\bin\splunk.exe"
if (-not (Test-Path $SplunkBin)) {
    Write-Host "Splunk not found at $SplunkBin. Install Splunk Enterprise first." -ForegroundColor Red
    exit 1
}

$User = $vars["SPLUNK_USERNAME"]
$Pass = $vars["SPLUNK_PASSWORD"]
$Auth = "${User}:${Pass}"
$WebPort = $vars["SPLUNK_WEB_PORT"]
if (-not $WebPort) { $WebPort = "8000" }

Write-Host "=== SignalSmith MCP Setup (Splunkbase app 7931) ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking current MCP status..." -ForegroundColor Cyan
python (Join-Path $Root "backend\scripts\check_mcp.py")
$checkExit = $LASTEXITCODE

Write-Host ""
Write-Host "=== Install Splunk MCP Server ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Option A — Splunk Web (recommended):" -ForegroundColor Yellow
Write-Host "  1. Open https://localhost:$WebPort"
Write-Host "  2. Apps -> Find More Apps -> search 'MCP Server'"
Write-Host "  3. Install 'Splunk MCP Server' (Splunkbase app 7931)"
Write-Host "     Direct link: https://splunkbase.splunk.com/app/7931"
Write-Host "  4. Restart Splunk:"
Write-Host "     & '$SplunkBin' restart -auth $Auth"
Write-Host "  5. Settings -> Access controls -> Roles -> your role"
Write-Host "     Enable: mcp_tool_execute (and mcp_server_access if shown)"
Write-Host ""

$LocalPackage = Get-ChildItem -Path $PackagesDir -Filter "*mcp*.tgz" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($LocalPackage) {
    Write-Host "Option B — Local package found:" -ForegroundColor Yellow
    Write-Host "  & '$SplunkBin' install app `"$($LocalPackage.FullName)`" -auth $Auth -update 1"
    Write-Host "  & '$SplunkBin' restart -auth $Auth"
    Write-Host ""
    $install = Read-Host "Install from $($LocalPackage.Name)? (y/N)"
    if ($install -eq "y") {
        & $SplunkBin install app $LocalPackage.FullName -auth $Auth -update 1
        & $SplunkBin restart -auth $Auth
        Start-Sleep -Seconds 8
    }
}

Write-Host "=== Verify ===" -ForegroundColor Cyan
python (Join-Path $Root "backend\scripts\check_mcp.py")

Write-Host ""
Write-Host "=== Deploy SignalSmith Splunk Dashboard ===" -ForegroundColor Cyan
Write-Host "  Open SignalSmith -> Splunk Dashboard -> 'Deploy to Splunk'"
Write-Host "  Or: POST http://localhost:8080/api/splunk/dashboard/deploy"
Write-Host ""
Write-Host "Splunk Web dashboard path after deploy:" -ForegroundColor Green
Write-Host "  https://localhost:$WebPort/en-US/app/search/signalsmith_operations"
Write-Host ""

if ($checkExit -ne 0) {
    Write-Host "MCP not yet active. Install app 7931 and restart Splunk." -ForegroundColor Yellow
}