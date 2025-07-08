# 🏆 MTG Chaos Commander Glicko-2 Calculator with Gradio UI

*A robust rating system for Magic: The Gathering Chaos Commander leagues, supporting multiplayer pods and draft events. Forked from and inspired by https://github.com/ahopeh/mtg-chaos-commander-glicko2*

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
[MIT License](LICENSE)

---

## 🚀 Features
- **Multiplayer Pods**: Handles 3-5 player games with tie resolution
- **Time Decay**: Automatic RD increase for inactive players  
- **Draft Integration**: Processes 1v1 matches alongside multiplayer  
- **First-Game Logic**: Special handling for new player volatility  

---

## 📦 Installation
This process assumes you have Python > 3.8 installed, setup, and functional. While this should work on any version of Python 3.8 or later, it was tested on 3.12.

```bash
# Clone the repository
git clone https://github.com/havenvanheusen/mtg-chaos-commander-glicko2-gradio.git

# Enter the project directory
cd mtg-chaos-commander-glicko2-gradio

# Create a new Python environment
python -m venv venv

# Activate the Python environment (only use one based on your platform)
source venv/bin/activate # For Mac and Linux
venv\Scripts\activate # For Windows

# Launch the UI
python3 gui.py
```

This was forked from and inspired by https://github.com/ahopeh/mtg-chaos-commander-glicko2