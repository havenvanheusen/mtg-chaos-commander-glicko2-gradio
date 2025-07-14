#!/bin/bash

# Define the project directory
REPO_DIR="mtg-chaos-commander-glicko2-gradio"

# Check if the project directory exists
if [ ! -d "$REPO_DIR" ]; then
    echo "Error: Project directory '$REPO_DIR' not found."
    echo "Please run the install.sh script first."
    read -p "Press enter to exit"
    exit 1
fi

cd "$REPO_DIR"

# Check if the virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment 'venv' not found in '$REPO_DIR'."
    echo "Please run the install.sh script to create it."
    read -p "Press enter to exit"
    exit 1
fi

# Check for the activation script
if [ ! -f "venv/bin/activate" ]; then
    echo "Error: Activation script not found. The virtual environment may be corrupt."
    echo "Please delete the 'venv' folder and run install.sh again."
    read -p "Press enter to exit"
    exit 1
fi

# Activate the virtual environment
source venv/bin/activate

# Verify Python is accessible within the venv
if ! command -v python >/dev/null; then
    echo "Error: Python is not working correctly within the virtual environment."
    echo "Please check your Python installation."
    read -p "Press enter to exit"
    exit 1
fi

# Verify that dependencies are installed by checking for a key package
if ! pip show gradio >/dev/null 2>&1; then
    echo "Error: Required Python packages are not installed."
    echo "Please run 'pip install -r requirements.txt' inside the activated virtual environment."
    read -p "Press enter to exit"
    exit 1
fi

echo "Launching the application..."
python gui.py

# Deactivate is called automatically when the script finishes
echo "Application closed."