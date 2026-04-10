@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"
set "SELECT_INDEX=%~1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%run_picker.ps1" "%SELECT_INDEX%"
exit /b %errorlevel%
