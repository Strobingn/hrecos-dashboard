# HRECOS API — Cornwall-on-Hudson / Newburgh
# Runs FastAPI on all interfaces so your Android phone can connect over Wi-Fi.

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host "HRECOS API Server" -ForegroundColor Cyan
Write-Host "=================" -ForegroundColor Cyan

$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
  $_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -ne 'WellKnown' -and $_.InterfaceAlias -notlike '*Switch*'
} | Select-Object -First 1).IPAddress

if (-not $ip) { $ip = "192.168.1.100" }

$env:DATABASE_URL = "sqlite+aiosqlite:///$Root/backend/hrecos.db"
$env:EMAIL_ENABLED = "false"
$env:SMS_ENABLED = "false"
$env:SLACK_ENABLED = "false"

Set-Location "$Root\backend"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error "Python not found. Install Python 3.10+ first."
}

Write-Host ""
Write-Host "API URL for Android app:" -ForegroundColor Green
Write-Host "  http://${ip}:8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "Docs:  http://${ip}:8000/docs" -ForegroundColor Gray
Write-Host "Health: http://${ip}:8000/health" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload