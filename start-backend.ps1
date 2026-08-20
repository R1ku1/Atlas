$backend = Join-Path $PSScriptRoot "backend"
Set-Location $backend

$venvActivate = Join-Path $backend ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    . $venvActivate
} else {
    Write-Warning "No .venv found at backend\.venv - using system Python. If this fails, create one with: python -m venv .venv"
}

uvicorn app.main:app --reload --port 8000