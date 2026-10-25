@echo off
setlocal
cd /d "%~dp0backend"
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed. Install Python 3.10-3.12 from python.org and tick "Add to PATH".
  pause & exit /b 1
)
if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate
if not exist .venv\installed.flag (
  echo Installing packages - the first time takes several minutes...
  pip install -r requirements.txt
  if errorlevel 1 ( echo Package install failed & pause & exit /b 1 )
  echo ok> .venv\installed.flag
)
start "" cmd /c "timeout /t 5 >nul & start http://localhost:8000"
echo Starting SmartAudit AI at http://localhost:8000  (press Ctrl+C to stop)
uvicorn app.main:app --port 8000
pause
