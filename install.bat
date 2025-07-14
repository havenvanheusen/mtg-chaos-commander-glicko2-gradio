@echo off

REM Function to download and install Git if needed
:installGit
echo Checking if Git is installed...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Please install Git from and ensure it's added to your PATH.
    pause
    exit /b 1
) else (
    echo Git is already installed. Continuing...
)

REM Check if Python is installed by attempting to get its version
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Please install Python from https://www.python.org/downloads/ and ensure it's added to your PATH.
    pause
    exit /b 1
)

REM Check if the repository already exists without cloning over existing data
if exist "mtg-chaos-commander-glicko2-gradio" (
    echo Directory 'mtg-chaos-commander-glicko2-gradio' already exists. Skipping clone to prevent overwriting.
) else (
    REM Clone the repository if it doesn't exist yet
    git clone https://github.com/havenvanheusen/mtg-chaos-commander-glicko2-gradio.git

    REM Check if git clone succeeded
    if %errorlevel% neq 0 (
        echo Failed to clone the repository. Please verify your internet connection and file permissions.
        pause
        exit /b 1
    )
)

REM Enter the project directory
cd mtg-chaos-commander-glicko2-gradio

REM Check if virtual environment already exists without overwriting it
if exist "venv" (
    echo Virtual environment 'venv' already exists. Assuming it's correctly set up and skipping its creation.
) else (
    REM Create a new Python environment only if it doesn't already exist
    python -m venv venv

    REM Check if creating virtual environment succeeded
    if %errorlevel% neq 0 (
        echo Failed to create the virtual environment.
        pause
        exit /b 1
    )
)

REM Activate the Python environment (only for Windows)
call venv\Scripts\activate.bat

REM Upgrade pip and install dependencies from requirements.txt
echo "Upgrading pip and installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Check if installation succeeded
if %errorlevel% neq 0 (
    echo Failed to install required packages. Please check requirements.txt and your internet connection.
    pause
    exit /b 1
)

REM Launch the UI
python gui.py

REM Deactivate the virtual environment when done (optional, but good practice)
deactivate