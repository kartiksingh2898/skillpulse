@echo off
title SkillPulse Control Panel
color 0B

cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" goto menu

echo ============================================================
echo           SkillPulse - Initializing Setup
echo ============================================================
echo.
echo  Python virtual environment (.venv) not found.
echo  Setting up .venv and installing dependencies from requirements.txt...
echo.
python -m venv "%~dp0.venv"
if errorlevel 1 (
    echo.
    echo  ERROR: Python is not installed or not added to system PATH.
    echo  Please install Python 3.11+ and check "Add Python to PATH".
    echo.
    pause
    goto end
)

echo  Installing required packages...
"%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip
"%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
echo.
echo  Setup completed successfully!
echo ============================================================
timeout /t 3 >nul

:menu
cls
echo ============================================================
echo                SKILLPULSE - MLOps Control Panel
echo ============================================================
echo.
echo   [1] Start Local Services   (FastAPI + Streamlit Dashboard)
echo   [2] Start Docker Stack     (Production Containers - Docker Compose)
echo   [3] Run Drift Monitor      (Evidently AI - saves HTML report)
echo   [4] Run Auto-Retrain       (Retrain if drift detected)
echo   [5] Force Retrain          (Retrain unconditionally)
echo   [6] Refresh Live Jobs      (Scrape Adzuna & Update Snapshot)
echo   [7] Reinstall Dependencies (pip install -r requirements.txt)
echo   [8] Exit
echo.
echo ============================================================
set /p choice="  Enter your choice [1-8]: "

if "%choice%"=="1" goto start_services
if "%choice%"=="2" goto start_docker
if "%choice%"=="3" goto drift_check
if "%choice%"=="4" goto auto_retrain
if "%choice%"=="5" goto force_retrain
if "%choice%"=="6" goto refresh_jobs
if "%choice%"=="7" goto install_deps
if "%choice%"=="8" goto end

echo.
echo   Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto menu

:start_services
cls
echo ============================================================
echo             Starting SkillPulse Local Services
echo ============================================================
echo.
echo  [1/2] Launching FastAPI Backend  ->  http://127.0.0.1:8000
start "SkillPulse - FastAPI Backend" cmd /k "title FastAPI Backend && cd /d "%~dp0" && "%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000"

timeout /t 2 /nobreak >nul

echo  [2/2] Launching Streamlit Dashboard  ->  http://localhost:8501
start "SkillPulse - Streamlit Dashboard" cmd /k "title Streamlit Dashboard && cd /d "%~dp0" && "%~dp0.venv\Scripts\python.exe" -m streamlit run streamlit_app/app.py --server.headless true --server.port 8501"

echo.
echo  Waiting for servers to warm up...
timeout /t 5 /nobreak >nul

start "" "http://127.0.0.1:8000/docs"
start "" "http://localhost:8501"

echo.
echo ============================================================
echo   Services launched! Open in your browser:
echo     FastAPI Docs : http://127.0.0.1:8000/docs
echo     Dashboard    : http://localhost:8501
echo.
echo   Press Ctrl+C in each window to stop the services.
echo ============================================================
echo.
pause
goto end

:start_docker
cls
echo ============================================================
echo            Starting SkillPulse Docker Compose Stack
echo ============================================================
echo.
echo  Checking Docker status...

where docker >nul 2>nul
if errorlevel 1 goto docker_missing

echo  Verifying Docker Engine connection...
docker info >nul 2>nul
if errorlevel 1 goto docker_failed

set DOCKER_DEFAULT_PLATFORM=linux/amd64

echo  Building & starting containers (DB + API + Dashboard)...
echo.

docker compose up --build -d
if errorlevel 1 goto docker_failed

echo.
echo  Waiting for Docker containers to warm up...
timeout /t 6 /nobreak >nul

start "" "http://127.0.0.1:8000/docs"
start "" "http://localhost:8501"

echo.
echo ============================================================
echo   Docker Stack Running! Open in your browser:
echo     FastAPI Docs : http://127.0.0.1:8000/docs
echo     Dashboard    : http://localhost:8501
echo.
echo   To view logs or stop containers:
echo     docker compose logs -f
echo     docker compose down
echo ============================================================
echo.
pause
goto end

:docker_missing
echo.
echo  NOTE: Docker is not installed on this PC.
echo  Launching Docker Desktop installer in background window...
echo  Switching to Local Python Mode (Option 1)...
echo.
where winget >nul 2>nul
if not errorlevel 1 start "Installing Docker" cmd /c "winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements"
timeout /t 3 >nul
goto start_services

:docker_failed
echo.
echo  NOTE: Docker engine is unresponsive or daemon is stopped.
echo  Switching to Local Python Mode (Option 1)...
echo.
timeout /t 3 >nul
goto start_services

:drift_check
cls
echo ============================================================
echo                    Running Drift Monitor
echo ============================================================
echo.
echo  Evidently AI is analyzing your data for drift...
echo  HTML report will be saved to drift_reports/
echo.
"%~dp0.venv\Scripts\python.exe" "%~dp0mlops\drift_monitor.py"
echo.
echo  Drift check complete. Check drift_reports/ for the report.
echo ============================================================
pause
goto end

:auto_retrain
cls
echo ============================================================
echo                  Auto-Retrain (Conditional)
echo ============================================================
echo.
echo  Checking drift status and retraining if needed...
echo.
"%~dp0.venv\Scripts\python.exe" "%~dp0mlops\retrain.py"
echo.
echo ============================================================
pause
goto end

:force_retrain
cls
echo ============================================================
echo                  Force Retrain (Unconditional)
echo ============================================================
echo.
echo  Retraining regardless of drift status...
echo.
"%~dp0.venv\Scripts\python.exe" "%~dp0mlops\retrain.py" --force
echo.
echo ============================================================
pause
goto end

:refresh_jobs
cls
echo ============================================================
echo           SkillPulse - Live Job Ingestion & Refresh
echo ============================================================
echo.
echo  Fetching live Adzuna jobs, extracting skills & updating snapshot...
echo.
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\refresh_snapshot.py"
echo.
echo ============================================================
pause
goto menu

:install_deps
cls
echo ============================================================
echo               Installing / Updating Requirements
echo ============================================================
echo.
"%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip
"%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
echo.
echo  All requirements installed successfully!
echo ============================================================
pause
goto menu

:end
echo.
echo ============================================================
echo   Goodbye - SkillPulse Control Panel closed.
echo ============================================================
pause