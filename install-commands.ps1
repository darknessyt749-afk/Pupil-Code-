$ErrorActionPreference = "Stop"
$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$bin = Join-Path $env:LOCALAPPDATA "PupilAI\bin"
New-Item -ItemType Directory -Force -Path $bin | Out-Null
$launcher = Join-Path $source "pupil.cmd"
if (-not (Test-Path $launcher)) { throw "pupil.cmd is missing from $source" }
Copy-Item $launcher (Join-Path $bin "pupil.cmd") -Force

# Add the launcher folder to this user's PATH if it is not already there.
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$parts = @($userPath -split ";" | Where-Object { $_ })
if ($parts -notcontains $bin) {
    $newPath = (@($parts) + $bin) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
}
Write-Host ""
Write-Host "Pupil AI command installed!" -ForegroundColor Magenta
Write-Host "Open a NEW PowerShell/Windows Terminal window, then run:" -ForegroundColor Cyan
Write-Host "  pupil" -ForegroundColor White
Write-Host "  pupil code" -ForegroundColor White
Write-Host ""
Write-Host "Both commands start your existing Pupil AI project. 'code' is an alias label for Pupil Code."
