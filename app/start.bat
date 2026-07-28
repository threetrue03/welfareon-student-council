@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [error] Virtual environment not found.
  echo Please run setup.bat first.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -c "import django, openpyxl, googleapiclient, google.oauth2.service_account" >nul 2>nul
if errorlevel 1 (
  echo [start] Installing missing requirements...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [error] Failed to install requirements.
    pause
    exit /b 1
  )
)

echo [start] Applying database migrations...
".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 (
  echo [error] Migration failed.
  pause
  exit /b 1
)

echo [start] Starting Django server...
".venv\Scripts\python.exe" manage.py runserver
pause
