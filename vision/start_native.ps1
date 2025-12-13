# Start Galatea Vision Service (Native)
Write-Host "Starting Galatea Vision Service (Native)..." -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

& .\venv\Scripts\Activate.ps1
python main.py



