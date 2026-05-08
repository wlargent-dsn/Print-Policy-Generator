@echo off
REM Batch script to run Automatic Print GPO Generator
REM Can be scheduled with Windows Task Scheduler

cd /d "%~dp0"

REM Run the Python script with a timeout of 5 minutes (300 seconds)
REM If it exceeds the timeout, the process will be terminated
timeout /t 1 >nul
tasklist | find "python.exe" >nul
if not errorlevel 1 (
    echo Previous Python process still running, killing it...
    taskkill /f /im python.exe
    timeout /t 2 >nul
)

REM Run the main script with timeout protection
REM Using start /wait with timeout to prevent infinite hangs
start /wait /B python main.py

REM Check exit code
if %errorlevel% neq 0 (
    echo GPO Generator failed with exit code %errorlevel%
    exit /b %errorlevel%
)

echo GPO Generator completed successfully
exit /b 0