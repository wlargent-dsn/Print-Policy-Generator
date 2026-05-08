@echo off
REM Batch script to run Automatic Print GPO Generator
REM Can be scheduled with Windows Task Scheduler

REM IMMEDIATE LOGGING - Create basic log before anything else
echo [%date% %time%] BATCH START: %0 %* > run_start.log
echo Working directory: %cd% >> run_start.log
echo User: %USERNAME% >> run_start.log
echo Computer: %COMPUTERNAME% >> run_start.log
echo. >> run_start.log

cd /d "%~dp0"

REM Create log directory if it doesn't exist
if not exist "logs" (
    echo [%date% %time%] Creating logs directory >> run_start.log
    mkdir logs 2>> run_start.log
    if errorlevel 1 (
        echo [%date% %time%] FAILED to create logs directory >> run_start.log
        type run_start.log
        exit /b 1
    )
) else (
    echo [%date% %time%] Logs directory exists >> run_start.log
)

REM Rotate old batch logs (keep last 30 days, max 10 files)
echo [%date% %time%] Rotating old batch logs... >> run_start.log
forfiles /p "logs" /m "run_*.log" /d -30 /c "cmd /c del @path" 2>> run_start.log
REM Keep only the 10 most recent run logs
for /f "skip=10" %%i in ('dir /b /o-d "logs\run_*.log" 2^>nul') do (
    echo [%date% %time%] Deleting old log: %%i >> run_start.log
    del "logs\%%i" 2>> run_start.log
)

REM Clean up the startup log file (keep only if there were errors)
if exist run_start.log (
    findstr /c:"FAILED" run_start.log >nul
    if errorlevel 1 (
        REM No errors found, safe to delete
        del run_start.log
    ) else (
        REM Errors found, move to logs for debugging
        move run_start.log logs\ >>nul 2>&1
    )
)

REM Simple log file name (no complex date parsing that might fail)
set LOG_FILE=logs\run_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log
REM Remove problematic characters from filename
set LOG_FILE=%LOG_FILE:/=%
set LOG_FILE=%LOG_FILE::=%
set LOG_FILE=%LOG_FILE: =0%

echo [%date% %time%] Log file will be: %LOG_FILE% >> run_start.log

REM Test if we can write to the log file
echo [%date% %time%] Testing log file creation > "%LOG_FILE%" 2>> run_start.log
if errorlevel 1 (
    echo [%date% %time%] FAILED to create log file: %LOG_FILE% >> run_start.log
    type run_start.log
    exit /b 1
) else (
    echo [%date% %time%] Log file created successfully >> run_start.log
)

REM Now continue with normal logging
echo [%date% %time%] Starting GPO Generator batch script >> "%LOG_FILE%"
echo [%date% %time%] Working directory: %cd% >> "%LOG_FILE%"
echo [%date% %time%] Command line: %0 %* >> "%LOG_FILE%"
echo [%date% %time%] User: %USERNAME% >> "%LOG_FILE%"
echo [%date% %time%] Computer: %COMPUTERNAME% >> "%LOG_FILE%"
echo [%date% %time%] Current directory permissions: >> "%LOG_FILE%"
icacls . >> "%LOG_FILE%" 2>&1
echo. >> "%LOG_FILE%"

REM Check if config.yaml exists
if not exist "config.yaml" (
    echo [%date% %time%] [ERROR] config.yaml not found in %cd% >> "%LOG_FILE%"
    echo [%date% %time%] Please copy config-example.yaml to config.yaml and configure it >> "%LOG_FILE%"
    type "%LOG_FILE%"
    exit /b 1
) else (
    echo [%date% %time%] [OK] config.yaml found >> "%LOG_FILE%"
)

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] [ERROR] Python is not installed or not in PATH >> "%LOG_FILE%"
    type "%LOG_FILE%"
    exit /b 1
) else (
    echo [%date% %time%] [OK] Python found >> "%LOG_FILE%"
    echo [%date% %time%] Getting Python version... >> "%LOG_FILE%"
    python --version >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo [%date% %time%] [WARNING] Could not get Python version >> "%LOG_FILE%"
    )
)

echo [%date% %time%] [DEBUG] About to check database >> "%LOG_FILE%"

REM Check for stuck database locks - if printers.db is locked, wait a moment
if exist "printers.db" (
    echo [%date% %time%] [INFO] printers.db exists, checking size >> "%LOG_FILE%"
    REM Use dir command instead of for loop to avoid potential issues
    dir /b printers.db >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo [%date% %time%] [WARNING] Cannot access printers.db - may be locked or permission issue >> "%LOG_FILE%"
    ) else (
        for /f "tokens=*" %%i in ('dir /-c printers.db ^| find "printers.db"') do (
            echo [%date% %time%] [OK] printers.db info: %%i >> "%LOG_FILE%"
        )
    )
) else (
    echo [%date% %time%] [INFO] printers.db does not exist, will be created >> "%LOG_FILE%"
)

echo [%date% %time%] [DEBUG] About to run Python script >> "%LOG_FILE%"

REM Run the Python script with timeout and output capture
echo [%date% %time%] [INFO] Starting GPO Generator at %date% %time% >> "%LOG_FILE%"

REM Test Python import before running
echo [%date% %time%] Testing Python imports... >> "%LOG_FILE%"
python -c "import sys; print('Python version:', sys.version)" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] [ERROR] Python basic test failed - cannot execute Python >> "%LOG_FILE%"
    echo [%date% %time%] Checking Python path... >> "%LOG_FILE%"
    where python >> "%LOG_FILE%" 2>&1
    echo [%date% %time%] Checking environment variables... >> "%LOG_FILE%"
    set PYTHON >> "%LOG_FILE%" 2>&1
    type "%LOG_FILE%"
    exit /b 1
)

REM Test importing our modules
echo [%date% %time%] Testing module imports... >> "%LOG_FILE%"
python -c "import yaml, sqlite3, smtplib; print('Required modules available')" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] [ERROR] Required modules not available - check pip install >> "%LOG_FILE%"
    echo [%date% %time%] Trying to install missing modules... >> "%LOG_FILE%"
    python -m pip install PyYAML >> "%LOG_FILE%" 2>&1
    echo [%date% %time%] Retrying module test... >> "%LOG_FILE%"
    python -c "import yaml, sqlite3, smtplib; print('Required modules available')" >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo [%date% %time%] [ERROR] Modules still not available after install attempt >> "%LOG_FILE%"
        type "%LOG_FILE%"
        exit /b 1
    )
)

REM Run with stderr visible for diagnostics - capture both stdout and stderr
echo [%date% %time%] [INFO] Executing main.py... >> "%LOG_FILE%"

REM First try a simple config import test
echo [%date% %time%] Testing config import... >> "%LOG_FILE%"
python -c "from config import Config; c = Config(); print('Config loaded successfully'); print('GPO path:', c.gpo_xml_path)" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] [ERROR] Config import failed - check config.yaml >> "%LOG_FILE%"
    type "%LOG_FILE%"
    exit /b 1
)

REM Test GPO path accessibility
echo [%date% %time%] Testing GPO path access... >> "%LOG_FILE%"
python -c "from config import Config; c = Config(); import os; print('Testing path:', c.gpo_xml_path); os.path.exists(os.path.dirname(c.gpo_xml_path)) and print('Path exists') or print('Path does not exist')" >> "%LOG_FILE%" 2>&1

REM Now run the full script
python main.py >> "%LOG_FILE%" 2>&1
set EXIT_CODE=%errorlevel%

REM Log completion
if %EXIT_CODE% equ 0 (
    echo [%date% %time%] [SUCCESS] GPO Generator completed successfully at %date% %time% >> "%LOG_FILE%"
) else (
    echo [%date% %time%] [ERROR] GPO Generator failed with exit code %EXIT_CODE% at %date% %time% >> "%LOG_FILE%"
)

REM Display the log file contents to console (for manual runs)
echo. >> "%LOG_FILE%"
echo [%date% %time%] === Batch script completed === >> "%LOG_FILE%"
type "%LOG_FILE%"

exit /b %EXIT_CODE%