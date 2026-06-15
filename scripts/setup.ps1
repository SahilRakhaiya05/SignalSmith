# SignalSmith AI - install dependencies (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example - edit Splunk credentials." -ForegroundColor Yellow
}

Write-Host "==> Python dependencies" -ForegroundColor Cyan
Set-Location "$Root\backend"
python -m pip install -r requirements.txt

Write-Host "==> Frontend dependencies" -ForegroundColor Cyan
Set-Location "$Root\frontend"
if (-not (Test-Path "node_modules")) { npm install }

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "  1. Edit .env (Splunk + MCP credentials)"
Write-Host "  2. .\scripts\install_mcp.ps1  (recommended)"
Write-Host "  3. .\scripts\start.ps1"
Write-Host "  4. Open http://localhost:8080"