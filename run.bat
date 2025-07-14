@echo off
setlocal

REM Define the project directory
set "REPO_DIR=mtg-chaos-commander-glicko2-gradio"

REM Check if the project directory exists
if not exist "%REPO_DIR%" (
    echo Error: Project directory '%REPO_DIR%' not found.
    echo Please run the install.bat script first.
    pause
    exit /b 1
)

cd "%REPO_DIR%"

REM Check if the virtual environment exists
if not exist "venv" (
    echo Error: Virtual environment 'venv' not found in '%REPO_DIR%'.
    echo Please run the install.bat script to create it.
    pause
    exit /b 1
)

REM Check for the activation script
if not exist "venv\\Scripts\\activate.bat" (
    echo Error: Activation script not found. The virtual environment may be corrupt.
    echo Please delete the 'venv' folder and run install.bat again.
    pause
    exit /b 1
)

REM Activate the virtual environment
call venv\\Scripts\\activate.bat

REM Verify Python is accessible within the venv
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not working correctly within the virtual environment.
    echo Please check your Python installation and PATH.
    pause
    exit /b 1
)

REM Verify that dependencies are installed by checking for a key package
pip show gradio >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Required Python packages are not installed.
    echo Please run 'pip install -r requirements.txt' inside the activated virtual environment.
    pause
    exit /b 1
)

echo Launching the application...
python gui.py

echo Application closed.
pause
endlocal