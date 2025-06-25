@echo off
chcp 65001 >nul
echo Starting Face Detection and Liveness Detection GUI (English Version)...
echo.
python face_detect_with_liveness_gui_en.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo Error: Failed to start the GUI application
    echo Please check if all dependencies are installed
    pause
)