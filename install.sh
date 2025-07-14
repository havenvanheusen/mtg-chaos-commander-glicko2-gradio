#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Function to check for a command
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for Git
echo "Checking if Git is installed..."
if ! command_exists git; then
    echo "Git is not installed. Please install Git and ensure it's in your PATH."
    read -p "Press enter to exit"
    exit 1
else
    echo "Git is already installed. Continuing..."
fi

# Check for Python 3
echo "Checking if Python 3 is installed..."
if ! command_exists python3; then
    echo "Python 3 is not installed. Please install Python 3 and ensure it's in your PATH."
    read -p "Press enter to exit"
    exit 1
else
    echo "Python 3 is already installed. Continuing..."
fi

REPO_DIR="mtg-chaos-commander-glicko2-gradio"

# Check if the repository directory already exists
if [ -d "$REPO_DIR" ]; then
    echo "Directory '$REPO_DIR' already exists. Skipping clone."
else
    # Clone the repository
    echo "Cloning repository..."
    git clone https://github.com/havenvanheusen/mtg-chaos-commander-glicko2-gradio.git
fi

# Enter the project directory
cd "$REPO_DIR"

# Check if virtual environment already exists
if [ -d "venv" ]; then
    echo "Virtual environment 'venv' already exists. Re-activating it."
else
    # Create a new Python virtual environment
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the Python environment
source venv/bin/activate

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found. Skipping dependency installation."
fi

# Launch the UI
echo "Launching the application..."
python3 gui.py

# Deactivate the virtual environment when the script is interrupted or finishes
deactivate
echo "Application closed."