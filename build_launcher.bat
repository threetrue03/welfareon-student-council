@echo off
chcp 65001 >nul
pushd "%~dp0"

if not exist "logs" mkdir "logs"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo [build] Building WelfareON launcher...
echo [build] 빌드 단계와 상세 로그를 아래에 출력합니다.
echo.

py -3.12 build_launcher.py
if errorlevel 1 goto fail

echo.
echo [build] Done. Check dist\WelfareOn_Launcher.exe and dist\복지온_Launcher.exe

popd
pause
exit /b 0

:fail
echo.
echo [build] Failed. Check logs\build_launcher.log
if exist "logs\build_launcher.log" type "logs\build_launcher.log"
popd
pause
exit /b 1
