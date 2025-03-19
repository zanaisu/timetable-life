@echo off
echo ===================================
echo    Timetable Application Launcher
echo ===================================
echo.

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher and try again.
    goto :exit
)

:: Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo Failed to create virtual environment.
        echo Please ensure Python venv module is available.
        goto :exit
    )
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Install or update dependencies
echo Checking dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Failed to install dependencies.
    goto :exit
)

:: Set environment variables
echo Setting environment variables...
set FLASK_APP=run.py
set FLASK_ENV=development

:: Check for .env file and create if not exists
if not exist .env (
    echo Creating default .env file...
    echo # Flask configuration > .env
    echo FLASK_APP=run.py >> .env
    echo FLASK_ENV=development >> .env
    echo SECRET_KEY=development-key >> .env
    echo. >> .env
    echo # Local Database >> .env
    echo LOCAL_DATABASE_URI=sqlite:///app.db >> .env
)

:: Check if database migrations are needed
echo Checking database status...
python -c "from flask_migrate import Migrate; from app import create_app, db; app = create_app(); migrate = Migrate(app, db)" 2>nul
if %ERRORLEVEL% neq 0 (
    echo Database needs initialization or migration...
    python -m flask db init 2>nul
    python -m flask db migrate -m "Initial migration" 2>nul
    python -m flask db upgrade
) else (
    echo Database appears to be properly configured. Upgrading if needed...
    python -m flask db upgrade
)

:: Start the application
echo.
echo ===================================
echo    Starting Timetable Application
echo ===================================
echo.
echo Access the application at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

flask run --host=0.0.0.0 --port=5000

:exit
echo.
echo Application terminated.
pause
