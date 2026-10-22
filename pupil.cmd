@echo off
setlocal
set "PUPIL_HOME=%USERPROFILE%\Music\pupil-code"
if not exist "%PUPIL_HOME%\pupil.py" (
  echo Pupil AI could not find:
  echo   "%PUPIL_HOME%\pupil.py"
  echo Edit PUPIL_HOME in this file to your project folder.
  pause
  exit /b 1
)
if /I "%~1"=="code" (
  echo Starting Pupil Code...
) else (
  echo Starting Pupil AI...
)
cd /d "%PUPIL_HOME%"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 pupil.py
) else (
  python pupil.py
)
endlocal
