@echo off
cd /d "%~dp0"
py -3 "%~dp0WelfareOn_Launcher.pyw"
if errorlevel 1 pause
