$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "Python not found. Install Python 3.10+ and reopen PowerShell." -ForegroundColor Red
  exit 1
}
python "$PSScriptRoot\pupil.py"
