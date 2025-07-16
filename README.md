# 🏆 MTG Chaos Commander Glicko-2 Calculator

*A robust rating system for Magic: The Gathering Chaos Commander leagues, now with a user-friendly web interface.*

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ Overview

This project provides a Glicko-2 rating system tailored for Magic: The Gathering, particularly for Chaos Commander and other multiplayer formats. It has evolved from a command-line tool to a full-fledged web application using Gradio, featuring a persistent SQLite database for robust data storage.

The application allows you to:
- **Manage Players**: Add, edit, and remove players from your league.
- **Track Matches**: Record multiplayer games (3-10 players) and their outcomes.
- **View Rankings**: See an updated leaderboard of all players.
- **Analyze Performance**: Plot and view the rating, RD (Rating Deviation), and volatility history for each player.
- **Data Integrity**: All data is stored in an SQLite database (`glicko2.db`) to ensure stability and prevent data loss.

---

## 📦 Installation

You can install the application using the provided scripts or by following the manual setup instructions.

### Automated Installation (Recommended)

#### Windows
1.  Download the `install.bat` script.
2.  Double-click the script to run it. It will:
    - Check for Python and Git.
    - Clone the repository.
    - Set up a virtual environment.
    - Install all required dependencies.
    - Launch the application.

#### macOS / Linux
1.  Download the `install.sh` script.
2.  Open your terminal and navigate to the directory where you saved the script.
3.  Make the script executable:
    ```bash
    chmod +x install.sh
    ```
4.  Run the script:
    ```bash
    ./install.sh
    ```

### Manual Installation

If you prefer to set up the project manually, follow these steps:

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/havenvanheusen/mtg-chaos-commander-glicko2-gradio.git
    cd mtg-chaos-commander-glicko2-gradio
    ```

2.  **Create and Activate a Virtual Environment**
    ```bash
    # For Windows
    python -m venv venv
    venv\Scripts\activate

    # For macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

---

## ▶️ How to Run

### Using the Run Scripts

Once installed, you can easily start the application using the provided run scripts:
-   **Windows**: Double-click `run.bat`
-   **macOS / Linux**: Run `./run.sh` in your terminal.

These scripts will activate the virtual environment and launch the Gradio interface.

### Manual Start

If you installed manually, make sure your virtual environment is activated, then run:
```bash
python gui.py
```
The application will be available at a local URL, typically `http://127.0.0.1:7860`.

---

## 📁 Project Structure

```
.
├── gui.py                  # Main Gradio application and Glicko-2 logic
├── database.py             # Handles all SQLite database interactions
├── requirements.txt        # Python dependencies
├── install.bat             # Windows installation script
├── install.sh              # macOS/Linux installation script
├── run.bat                 # Windows run script
├── run.sh                  # macOS/Linux run script
├── glicko2.db              # SQLite database file (created on first run)
├── README.md               # This file
└── LICENSE                 # MIT License
