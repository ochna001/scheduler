@echo off
echo ============================================
echo  Classroom Scheduling Optimizer GUI
echo ============================================
echo.
echo Starting application...
echo.

python scheduler_gui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to start GUI
    echo.
    echo Please ensure:
    echo 1. Python is installed
    echo 2. Dependencies are installed: pip install pulp pandas openpyxl numpy
    echo.
    pause
)
