# SignalSmith AI - Windows startup script
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Read-EnvValue([string]$Name, [string]$Default) {
  $envFile = Join-Path $Root ".env"
  if (-not (Test-Path $envFile)) { return $Default }
  foreach ($line in Get-Content $envFile) {
    if ($line -match "^\s*$Name=(.*)$") { return $matches[1].Trim() }
  }
  return $Default
}

$webScheme = Read-EnvValue "SPLUNK_WEB_SCHEME" "http"
$webPort = Read-EnvValue "SPLUNK_WEB_PORT" "8000"
$apiScheme = Read-EnvValue "SPLUNK_API_SCHEME" "https"
$apiPort = Read-EnvValue "SPLUNK_API_PORT" "8089"
$defaultMcp = "{0}://localhost:{1}/services/mcp" -f $apiScheme, $apiPort
$mcpUrl = Read-EnvValue "SPLUNK_MCP_URL" $defaultMcp

Write-Host "==> Building frontend..." -ForegroundColor Cyan
Set-Location "$Root\frontend"
if (-not (Test-Path "node_modules")) { npm install }
npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }

Write-Host "==> Stopping old backend on port 8080..." -ForegroundColor Cyan
Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Write-Host "==> Starting backend (serves UI + API on port 8080)..." -ForegroundColor Cyan
Set-Location "$Root\backend"
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080" -WorkingDirectory "$Root\backend" -WindowStyle Normal

Start-Sleep -Seconds 3
try {
  $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/health" -TimeoutSec 10
  Write-Host "Backend healthy. Splunk: $($health.splunk_connection)" -ForegroundColor Green
} catch {
  Write-Host "Backend not responding yet. Check the Python window." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "SignalSmith is ready:" -ForegroundColor Green
Write-Host "  UI + API:       http://localhost:8080"
Write-Host "  API Docs:       http://localhost:8080/docs"
Write-Host "  Integrations:   http://localhost:8080/api/integrations/status"
Write-Host "  Splunk Web:     ${webScheme}://localhost:${webPort}"
Write-Host "  Splunk API:     ${apiScheme}://localhost:${apiPort}"
Write-Host "  Splunk MCP:     $mcpUrl"
Write-Host ""
Write-Host "CLI commands:" -ForegroundColor Cyan
Write-Host "  python -m app.cli health"
Write-Host "  python -m app.cli integrations"
Write-Host "  python -m app.cli bootstrap"
Write-Host "  python -m app.cli run"
Write-Host ""
Write-Host "Open http://localhost:8080 in your browser." -ForegroundColor Green