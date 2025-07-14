import sqlite3
from datetime import datetime

DB_FILE = "glicko2.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """Creates the necessary database tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Player table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            rating REAL NOT NULL,
            rd REAL NOT NULL,
            volatility REAL NOT NULL,
            last_played_date TEXT,
            season_start TEXT NOT NULL,
            games INTEGER NOT NULL
        )
    ''')
    
    # Game history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL
        )
    ''')
    
    # Placements table to link players and games
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS placements (
            game_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            placement INTEGER NOT NULL,
            FOREIGN KEY (game_id) REFERENCES game_history(id) ON DELETE CASCADE,
            FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
            PRIMARY KEY (game_id, player_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_player_db(name, rating, rd, volatility, season_start):
    """Adds a new player to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO players (name, rating, rd, volatility, season_start, games) VALUES (?, ?, ?, ?, ?, 0)",
        (name, rating, rd, volatility, season_start.strftime("%Y-%m-%d"))
    )
    conn.commit()
    conn.close()

def get_player_by_name_db(name):
    """Retrieves a single player by name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE name = ?", (name,))
    player = cursor.fetchone()
    conn.close()
    return player

def get_all_players_db():
    """Retrieves all players from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players ORDER BY name")
    players = cursor.fetchall()
    conn.close()
    return players

def update_player_db(player_id, rating, rd, volatility, last_played_date, games):
    """Updates a player's stats in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE players 
        SET rating = ?, rd = ?, volatility = ?, last_played_date = ?, games = ?
        WHERE id = ?
        """,
        (rating, rd, volatility, last_played_date.strftime("%Y-%m-%d"), games, player_id)
    )
    conn.commit()
    conn.close()

def edit_player_name_db(old_name, new_name):
    """Updates a player's name in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE players SET name = ? WHERE name = ?", (new_name, old_name))
    conn.commit()
    conn.close()

def remove_player_db(name):
    """Removes a player from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM players WHERE name = ?", (name,))
    conn.commit()
    conn.close()

def add_match_db(game_date, placements):
    """Adds a match and its placements to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Add the game to game_history
    cursor.execute("INSERT INTO game_history (date) VALUES (?)", (game_date.strftime("%Y-%m-%d"),))
    game_id = cursor.lastrowid
    
    # Add each player's placement
    placement_data = []
    for player, placement in placements:
        player_record = get_player_by_name_db(player.name)
        if player_record:
            placement_data.append((game_id, player_record['id'], placement))

    cursor.executemany("INSERT INTO placements (game_id, player_id, placement) VALUES (?, ?, ?)", placement_data)
    
    conn.commit()
    conn.close()

def get_game_history_db():
    """Retrieves the entire game history from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT gh.id, gh.date, p.name, pl.placement
        FROM game_history gh
        JOIN placements pl ON gh.id = pl.game_id
        JOIN players p ON pl.player_id = p.id
        ORDER BY gh.date, pl.placement
    """)
    
    games = {}
    for row in cursor.fetchall():
        game_id = row['id']
        if game_id not in games:
            games[game_id] = {
                'id': game_id,
                'date': row['date'],
                'placements': []
            }
        games[game_id]['placements'].append((row['name'], row['placement']))
        
    conn.close()
    # Return a list of games, sorted by date descending
    return sorted(games.values(), key=lambda x: x['date'], reverse=True)

def delete_match_db(game_id):
    """Deletes a match from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # The ON DELETE CASCADE foreign key will handle deleting from placements table
    cursor.execute("DELETE FROM game_history WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()

# Call setup_database() when the module is imported to ensure tables exist.
setup_database()