@echo off
title SkillPulse Control Panel
echo ============================================================
echo       ^^  SKILLPULSE — MLOps Control Panel
echo ============================================================
echo.
echo  [1] Start All Services  (FastAPI + Streamlit Dashboard)
echo  [2] Run Drift Monitor   (Evidently AI — saves HTML report)
echo  [3] Run Auto-Retrain    (Retrain if drift detected)
echo  [4] Force Retrain       (Retrain unconditionally)
echo  [5] Exit
echo.
set /p choice="Enter your choice [1-5]: "

if "%choice%"=="1" goto start_services
if "%choice%"=="2" goto drift_check
if "%choice%"=="3" goto auto_retrain
if "%choice%"=="4" goto force_retrain
if "%choice%"=="5" goto end
echo Invalid choice. Please run again.
goto end

:start_services
echo.
echo [1/2] Launching FastAPI Backend on http://127.0.0.1:8000 ...
start "SkillPulse — FastAPI Backend" cmd /k "title FastAPI Backend && uvicorn app.main:app --reload"
timeout /t 2 /nobreak >nul
echo [2/2] Launching Streamlit Dashboard on http://localhost:8501 ...
start "SkillPulse — Streamlit Dashboard" cmd /k "title Streamlit Dashboard && streamlit run streamlit_app/app.py"
echo.
echo ============================================================
echo  Services launched! Open in your browser:
echo    FastAPI Docs : http://127.0.0.1:8000/docs
echo    Dashboard    : http://localhost:8501
echo  Press Ctrl+C in each window to stop.
echo ============================================================
goto end

:drift_check
echo.
echo Running Evidently AI Drift Monitor...
echo HTML report will be saved to drift_reports/
echo.
python mlops/drift_monitor.py
echo.
echo Drift check complete. Check drift_reports/ for the HTML report.
pause
goto end

:auto_retrain
echo.
echo Checking drift status and retraining if needed...
echo.
python mlops/retrain.py
echo.
pause
goto end

:force_retrain
echo.
echo FORCE RETRAIN — Retraining regardless of drift status...
echo.
python mlops/retrain.py --force
echo.
pause
goto end

:end
echo.
echo Goodbye!
