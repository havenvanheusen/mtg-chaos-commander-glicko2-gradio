# 🏆 MTG Chaos Commander Glicko-2 Calculator

*A robust rating system for Magic: The Gathering Chaos Commander leagues, supporting multiplayer pods and draft events.*

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
```bash
git clone https://github.com/ahopeh/mtg-chaos-commander-glicko2.git
cd mtg-chaos-commander-glicko2
python3 glicko2_calculator.py

Enter season start date (YYYY-MM-DD): 2025-01-01

[1] Add new player
[2] Select existing player

Placement for PlayerA: 1  # 1st place
Placement for PlayerB: 2  # 2nd place

```python
# Example output after a game:
🥇 1. Alice (Rating: 1624.3 ▲+15.2)
🥈 2. Bob (Rating: 1555.7 ▼-8.4)
🥉 3. Charlie (Rating: 1501.1 ▼-12.6)
```

.
├── glicko2_calculator.py  # Main logic
├── README.md             # This file
├── LICENSE               # MIT License
└── .gitignore            # Ignores Python cache files
