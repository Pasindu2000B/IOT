@echo off
REM Auto-start Inference Service on Windows boot
REM This script runs main.py with auto-restart on crash

cd /d "C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction"

echo ========================================
echo  Inference Service Auto-Start
echo ========================================
echo.
echo Starting inference service...
echo Dashboard: http://localhost:8000
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

:restart
python main.py
echo.
echo [%date% %time%] Service stopped. Restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto restart
