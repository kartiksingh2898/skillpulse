@echo off
setlocal
title SkillPulse Control Panel
color 0B

:menu
cls
echo ============================================================
echo                SKILLPULSE — MLOps Control Panel
echo ============================================================
echo.
echo   [1] Start All Services   (FastAPI + Streamlit Dashboard)
echo   [2] Run Drift Monitor    (Evidently AI — saves HTML report)
echo   [3] Run Auto-Retrain     (Retrain if drift detected)
echo   [4] Force Retrain        (Retrain unconditionally)
echo   [5] Exit
echo.
echo ============================================================
set /p choice="  Enter your choice [1-5]: "

if "%choice%"=="1" goto start_services
if "%choice%"=="2" goto drift_check
if "%choice%"=="3" goto auto_retrain
if "%choice%"=="4" goto force_retrain
if "%choice%"=="5" goto end

echo.
echo   Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto menu

:start_services
cls
echo ============================================================
echo                   Starting SkillPulse Services
echo ============================================================
echo.
echo  [1/2] Launching FastAPI Backend  ->  http://127.0.0.1:8000
start "SkillPulse - FastAPI Backend" cmd /k "title FastAPI Backend && cd /d %~dp0 && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload"

timeout /t 2 /nobreak >nul

echo  [2/2] Launching Streamlit Dashboard  ->  http://localhost:8501
start "SkillPulse - Streamlit Dashboard" cmd /k "title Streamlit Dashboard && cd /d %~dp0 && call .venv\Scripts\activate.bat && python -m streamlit run streamlit_app/app.py --server.headless true"

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

:drift_check
cls
echo ============================================================
echo                    Running Drift Monitor
echo ============================================================
echo.
echo  Evidently AI is analyzing your data for drift...
echo  HTML report will be saved to drift_reports/
echo.
call .venv\Scripts\activate.bat
python mlops\drift_monitor.py
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
call .venv\Scripts\activate.bat
python mlops\retrain.py
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
call .venv\Scripts\activate.bat
python mlops\retrain.py --force
echo.
echo ============================================================
pause
goto end

:end
echo.
echo ============================================================
echo   Goodbye — SkillPulse Control Panel closed.
echo ============================================================
timeout /t 2 /nobreak >nul
endlocal
exit /b