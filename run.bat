@echo off
REM Batch script to run Automatic Print GPO Generator
REM Can be scheduled with Windows Task Scheduler

cd /d "%~dp0"

REM Run the Python script
python main.py

REM Check exit code
if %errorlevel% neq 0 (
    echo GPO Generator failed with exit code %errorlevel%
    exit /b %errorlevel%
)

echo GPO Generator completed successfully
exit /b 0