@echo off
:: SkillPulse Daily Job Refresh
:: Runs scripts/refresh_snapshot.py to pull latest jobs from MySQL + push to GitHub
:: Schedule this in Windows Task Scheduler to run daily at 6:00 AM

cd /d "%~dp0"
echo.
echo ============================================================
echo     SkillPulse - Daily Job Data Refresh
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found. Please run start_services.bat first.
    pause
    exit /b 1
)

echo Refreshing job listings with apply URLs...
".venv\Scripts\python.exe" scripts\refresh_snapshot.py

echo.
echo ============================================================
echo  Done! Streamlit Cloud will update within 1 minute.
echo ============================================================
echo.
pause
