@echo off
rem ---------------------------------------------------------------------------
rem  AtliQ ContractIQ launcher (double-click me).
rem  Starts the local server on http://127.0.0.1:8000 and opens it in your browser.
rem  Keep this window open while you use the app; close it to stop the server.
rem  Optional AI: set GROQ_API_KEY (or ANTHROPIC_API_KEY) in your environment first.
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"
title AtliQ ContractIQ - local server
set "URL=http://127.0.0.1:8000"
set "PY=.venv\Scripts\python.exe"

rem Already running? Just open the browser.
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 '%URL%/api/meta' | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
if not errorlevel 1 (
  echo ContractIQ is already running. Opening %URL%
  start "" "%URL%"
  exit /b 0
)

rem First run: create the Python environment.
if not exist "%PY%" (
  echo [setup] Creating Python virtual environment...
  python -m venv .venv || goto :nopython
  "%PY%" -m pip install -r requirements.txt || goto :fail
)

rem Build the React frontend if it has not been built yet.
if not exist "frontend\dist\index.html" (
  if exist "%ProgramFiles%\nodejs\npm.cmd" set "PATH=%ProgramFiles%\nodejs;%PATH%"
  where npm >nul 2>nul || goto :nonode
  echo [setup] Building the frontend...
  pushd frontend
  call npm install || (popd & goto :fail)
  call npm run build || (popd & goto :fail)
  popd
)

if defined GROQ_API_KEY (
  echo AI: Groq key found - AI features available, consent is asked per request.
) else if defined ANTHROPIC_API_KEY (
  echo AI: Anthropic key found - AI features available, consent is asked per request.
) else (
  echo AI: no API key set - running in DEMO MODE ^(rules + local search only^).
)
echo.
echo Starting ContractIQ at %URL% ...
echo Keep this window open while you use the app. Close it (or press Ctrl+C) to stop.
echo.

rem Open the browser as soon as the server answers (in the background).
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "for ($i = 0; $i -lt 90; $i++) { try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 '%URL%/api/meta' | Out-Null; Start-Process '%URL%'; break } catch { Start-Sleep -Seconds 1 } }"

"%PY%" run.py
goto :eof

:nopython
echo.
echo Python was not found. Install Python 3.11+ from https://www.python.org/ and run this file again.
pause
exit /b 1

:nonode
echo.
echo The frontend has not been built and Node.js/npm was not found.
echo Install Node.js LTS (https://nodejs.org/) and run this file again.
pause
exit /b 1

:fail
echo.
echo Setup failed - see the messages above.
pause
exit /b 1
