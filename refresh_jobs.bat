@echo off
:: SkillPulse Daily Live Job Ingestion & Snapshot Refresh
:: Runs scripts/refresh_snapshot.py to pull live Adzuna jobs + update snapshot + push to GitHub

cd /d "%~dp0"
echo.
echo ============================================================
echo      SkillPulse - Daily Live Job Ingestion & Refresh
echo ============================================================
echo.

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found (.venv\Scripts\python.exe).
    echo Please run start_services.bat first to set up the environment.
    pause
    exit /b 1
)

echo [1/3] Executing live job ingestion & snapshot refresh...
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\refresh_snapshot.py"

echo.
echo ============================================================
echo  Execution finished! Streamlit Cloud will update shortly.
echo ============================================================
echo.
pause
