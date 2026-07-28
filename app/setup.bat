@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [setup] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [error] Failed to create virtual environment.
    pause
    exit /b 1
  )
) else (
  echo [setup] Virtual environment already exists.
)

echo [setup] Installing requirements...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo [error] Failed to upgrade pip.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [error] Failed to install requirements.
  pause
  exit /b 1
)

echo [setup] Applying database migrations...
".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 (
  echo [error] Migration failed.
  pause
  exit /b 1
)

echo [setup] Done.
pause
