$root = $PSScriptRoot

$backendScript = Join-Path $root "start-backend.ps1"
$frontendScript = Join-Path $root "start-frontend.ps1"

if (-not (Test-Path $backendScript)) {
    Write-Error "Missing start-backend.ps1 next to run.ps1"
    exit 1
}
if (-not (Test-Path $frontendScript)) {
    Write-Error "Missing start-frontend.ps1 next to run.ps1"
    exit 1
}

Write-Host "Starting Atlas..." -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-File", $backendScript
Write-Host "  Backend  -> http://localhost:8000  (new window)" -ForegroundColor Green

Start-Process powershell -ArgumentList "-NoExit", "-File", $frontendScript
Write-Host "  Frontend -> http://localhost:5173  (new window)" -ForegroundColor Green

Write-Host ""
Write-Host "Two windows opened. Close them, or Ctrl+C inside each, to stop Atlas." -ForegroundColor Yellow