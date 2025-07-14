import gradio as gr
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import json
from collections import defaultdict
import math
import os
import database as db

# --- Glicko-2 Implementation ---

# Glicko-2 Constants
PI_SQUARED = math.pi ** 2
SCALING_FACTOR = 173.7178
EPSILON = 0.000001
MAX_RATING_CHANGE = 250

class Player:
    def __init__(self, name, rating=1500, rd=350, volatility=0.06, last_played_date=None, season_start=None, player_id=None, games=0):
        """Initialize a player with Glicko-2 rating parameters."""
        self.id = player_id
        self.name = name
        self.rating = rating
        self.rd = rd
        self.volatility = volatility
        self.last_played_date = last_played_date or season_start or datetime.today().date()
        self.games_today = 0
        self.season_start = season_start or datetime.today().date()
        self.games = games

    def to_glicko2_scale(self):
        """Convert rating and RD to Glicko-2 scale."""
        return (self.rating - 1500) / SCALING_FACTOR, self.rd / SCALING_FACTOR

    def from_glicko2_scale(self, mu, phi):
        """Convert Glicko-2 scale mu and phi back to rating and RD."""
        self.rating = mu * SCALING_FACTOR + 1500
        self.rd = phi * SCALING_FACTOR

    def days_since_last_played(self, current_date):
        """Calculate days since last played or season start."""
        reference = self.last_played_date or self.season_start
        return (current_date - reference).days

def glicko2_g(phi):
    """Calculate the Glicko-2 g function for RD scaling."""
    return 1 / math.sqrt(1 + 3 * phi**2 / PI_SQUARED)

def update_volatility(mu, phi, volatility, v, delta, tau=0.5):
    """Update player volatility using Glicko-2 iterative method."""
    a = math.log(volatility ** 2)
    x0 = a
    while True:
        d = phi**2 + v + math.exp(x0)
        h1 = -(x0 - a) / (tau**2) - 0.5 * math.exp(x0) / d + 0.5 * math.exp(x0) * (delta / d)**2
        h2 = -1 / (tau**2) - 0.5 * math.exp(x0) * (phi**2 + v) / (d**2) + \
             0.5 * delta**2 * math.exp(x0) * (phi**2 + v - math.exp(x0)) / (d**3)
        x1 = x0 - h1 / h2
        if abs(x1 - x0) < EPSILON:
            break
        x0 = x1
    return math.exp(x1 / 2)

# No longer needed, replaced by database functions

def update_rd_for_inactivity(player, game_date):
    """Update player's RD based on days since last played."""
    if player.last_played_date != game_date:
        player.games_today = 0
        days = player.days_since_last_played(game_date)
        phi = player.rd / SCALING_FACTOR
        phi_star = math.sqrt(phi**2 + player.volatility**2 * days)
        player.rd = min(phi_star * SCALING_FACTOR, 350)

def calculate_outcomes(placements, num_players, tied_at_place):
    """Calculate Glicko-2 outcomes for each player pair, handling ties."""
    outcomes = {}
    for player, place in placements:
        results = []
        for opp, opp_place in placements:
            if opp != player:
                opp_mu, opp_phi = opp.to_glicko2_scale()
                if place < opp_place:
                    outcome = 1.0
                elif place > opp_place:
                    outcome = 0.0
                else:
                    outcome = (num_players - place) / (num_players - 1) / tied_at_place[place]
                results.append((opp_mu, opp_phi, outcome))
        outcomes[player] = results
    return outcomes

def update_player_ratings(player, mu, phi, results, is_first_game_today, num_players, tied_at_place, placements):
    """Update a player's rating, RD, and volatility based on game outcomes."""
    if not is_first_game_today:
        return
    opp_mus, opp_phis, outcomes = zip(*results)
    g_phis = [glicko2_g(phi) for phi in opp_phis]
    E = [1 / (1 + math.exp(-g * (mu - opp_mu))) for g, opp_mu in zip(g_phis, opp_mus)]
    tie_factor = sum(1 for _, p in placements if tied_at_place.get(p, 1) > 1) / num_players
    v = 1 / sum(g**2 * e * (1 - e) * (1 + tie_factor) for g, e in zip(g_phis, E))
    delta = v * sum(g * (outcome - e) for g, e, outcome in zip(g_phis, E, outcomes)) * math.sqrt(num_players - 1)
    new_vol = update_volatility(mu, phi, player.volatility, v, delta)
    phi_star = math.sqrt(phi**2 + new_vol**2)
    phi_prime = 1 / math.sqrt(1 / phi_star**2 + 1 / v)
    mu_prime = mu + phi_prime**2 * sum(g * (outcome - e) for g, e, outcome in zip(g_phis, E, outcomes))
    delta_cap = MAX_RATING_CHANGE / SCALING_FACTOR * math.sqrt(num_players - 1)
    mu_prime = max(min(mu_prime, mu + delta_cap), mu - delta_cap)
    player.from_glicko2_scale(mu_prime, phi_prime)
    player.volatility = new_vol

def process_game(players, placements, game_date, save_history=True):
    """Process a multiplayer game, updating player ratings and saving to history."""
    tied_at_place = defaultdict(int)
    for _, place in placements:
        tied_at_place[place] += 1

    for player in players:
        update_rd_for_inactivity(player, game_date)

    num_players = len(players)
    outcomes = calculate_outcomes(placements, num_players, tied_at_place)

    for player, results in outcomes.items():
        mu, phi = player.to_glicko2_scale()
        is_first_game_today = player.games_today == 0
        update_player_ratings(player, mu, phi, results, is_first_game_today, num_players, tied_at_place, placements)
        player.last_played_date = game_date
        player.games_today += 1

    if save_history:
        db.add_match_db(game_date, placements)

# --- Data Loading and State Management ---

def get_player_names():
    """Returns a list of player names from the database."""
    players = db.get_all_players_db()
    return [p['name'] for p in players]

def get_players_df():
    """Returns a pandas DataFrame of the current players from the database."""
    players = db.get_all_players_db()
    if not players:
        return pd.DataFrame({
            "Name": [], "Rating": [], "RD": [], "Volatility": [], "Last Played": [], "Games": []
        })
    player_data = {
        "Name": [p['name'] for p in players],
        "Rating": [round(p['rating'], 2) for p in players],
        "RD": [round(p['rd'], 2) for p in players],
        "Volatility": [round(p['volatility'], 4) for p in players],
        "Last Played": [p['last_played_date'] if p['last_played_date'] else "N/A" for p in players],
        "Games": [p['games'] for p in players]
    }
    return pd.DataFrame(player_data)

# --- GUI Functions ---

def add_player(name, rating, rd, volatility):
    """Adds a new player to the database and updates dropdowns."""
    if not name:
        status = "Player name cannot be empty."
        return (status, get_players_df()) + (gr.update(),) * 13

    if db.get_player_by_name_db(name):
        status = f"Player '{name}' already exists."
        return (status, get_players_df()) + (gr.update(),) * 13

    db.add_player_db(name, float(rating), float(rd), float(volatility), datetime.today().date())

    status = f"Player '{name}' added successfully."
    updated_player_list = get_player_names()
    dropdown_update = gr.update(choices=updated_player_list)

    return (status, get_players_df()) + (dropdown_update,) * 13

def add_match_ui(match_date_str, *player_data):
    """Processes a match from the UI, updates ratings, and saves to the database."""
    try:
        game_date = datetime.strptime(match_date_str, "%Y-%m-%d").date()
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD.", get_players_df(), None, get_game_history_df()

    all_players_records = db.get_all_players_db()
    all_players_map = {p['name']: Player(
        player_id=p['id'],
        name=p['name'],
        rating=p['rating'],
        rd=p['rd'],
        volatility=p['volatility'],
        last_played_date=datetime.strptime(p['last_played_date'], "%Y-%m-%d").date() if p['last_played_date'] else None,
        season_start=datetime.strptime(p['season_start'], "%Y-%m-%d").date(),
        games=p['games']
    ) for p in all_players_records}

    placements = []
    num_players_in_match = len(player_data) // 2
    for i in range(num_players_in_match):
        player_name = player_data[i*2]
        placement_str = player_data[i*2 + 1]
        
        if player_name and placement_str:
            try:
                placement = int(placement_str)
                player = all_players_map.get(player_name)
                if player:
                    placements.append((player, placement))
            except (ValueError, StopIteration):
                return f"Invalid data for player or placement.", get_players_df(), None, get_game_history_df()

    if len(placements) < 2:
        return "A match must have at least 2 players.", get_players_df(), None, get_game_history_df()

    game_players = [p for p, _ in placements]

    if len(game_players) != len(set(p.name for p in game_players)):
        return "Error: A player cannot be entered more than once in the same match.", get_players_df(), None, get_game_history_df()
    
    # Process the game without saving to history yet
    process_game(game_players, placements, game_date, save_history=False)
    
    # Add the match to the database
    db.add_match_db(game_date, placements)

    # Update player stats in the database
    for p in game_players:
        p.games += 1
        db.update_player_db(p.id, p.rating, p.rd, p.volatility, game_date, p.games)

    results_summary = f"Match on {game_date} processed.\n\nNew Ratings:\n"
    for p in sorted(game_players, key=lambda x: x.rating, reverse=True):
        results_summary += f"- {p.name}: {p.rating:.2f} (RD: {p.rd:.2f})\n"

    return results_summary, get_players_df(), get_players_df(), get_game_history_df()


def plot_player_history(player_name):
    """Plots the rating, RD, and volatility history for a selected player from the database."""
    if not player_name:
        return None, None, None

    history = db.get_game_history_db()
    if not history:
        return None, None, None

    # Sort history chronologically (it's already sorted descending, so reverse)
    history.sort(key=lambda x: datetime.strptime(x['date'], "%Y-%m-%d").date())

    # Get all unique player names from the database
    all_players_records = db.get_all_players_db()
    sim_players = {p['name']: Player(
        player_id=p['id'],
        name=p['name'],
        # Initialize with default values for a clean simulation
        rating=1500,
        rd=350,
        volatility=0.06,
        season_start=datetime.strptime(p['season_start'], "%Y-%m-%d").date(),
        last_played_date=datetime.strptime(p['season_start'], "%Y-%m-%d").date()
    ) for p in all_players_records}

    player_history_data = {
        'date': [],
        'rating': [],
        'rd': [],
        'volatility': []
    }

    # Simulate game by game to get historical data
    for game in history:
        game_date = datetime.strptime(game['date'], "%Y-%m-%d").date()
        
        game_participants_names = [p_name for p_name, _ in game['placements']]

        if player_name in game_participants_names:
            player_obj = sim_players[player_name]
            player_history_data['date'].append(game_date)
            player_history_data['rating'].append(player_obj.rating)
            player_history_data['rd'].append(player_obj.rd)
            player_history_data['volatility'].append(player_obj.volatility)

        # Prepare data for process_game
        placements_for_processing = []
        game_players_for_processing = []
        for p_name, place in game['placements']:
            if p_name in sim_players:
                player_obj = sim_players[p_name]
                placements_for_processing.append((player_obj, place))
                game_players_for_processing.append(player_obj)
        
        if len(game_players_for_processing) >= 2:
            # This will update the sim_players objects in place
            process_game(game_players_for_processing, placements_for_processing, game_date, save_history=False)

    if not player_history_data['date']:
        return None, None, None

    # Plotting logic
    fig_rating, ax_rating = plt.subplots()
    ax_rating.plot(player_history_data['date'], player_history_data['rating'], marker='o')
    ax_rating.set_title(f"{player_name}'s Rating Over Time")
    ax_rating.set_xlabel("Date")
    ax_rating.set_ylabel("Rating")
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    fig_rd, ax_rd = plt.subplots()
    ax_rd.plot(player_history_data['date'], player_history_data['rd'], marker='o', color='orange')
    ax_rd.set_title(f"{player_name}'s RD Over Time")
    ax_rd.set_xlabel("Date")
    ax_rd.set_ylabel("Rating Deviation (RD)")
    plt.xticks(rotation=45)
    plt.tight_layout()

    fig_vol, ax_vol = plt.subplots()
    ax_vol.plot(player_history_data['date'], player_history_data['volatility'], marker='o', color='green')
    ax_vol.set_title(f"{player_name}'s Volatility Over Time")
    ax_vol.set_xlabel("Date")
    ax_vol.set_ylabel("Volatility")
    plt.xticks(rotation=45)
    plt.tight_layout()

    return fig_rating, fig_rd, fig_vol

def get_game_history_df():
    """Returns a pandas DataFrame of the game history from the database."""
    history = db.get_game_history_db()
    if not history:
        return pd.DataFrame(columns=["Match ID", "Date", "Placements"])

    history_data = []
    for game in history:
        placements_str = ", ".join([f"{p[0]} ({p[1]})" for p in sorted(game['placements'], key=lambda x: x[1])])
        history_data.append({
            "Match ID": game['id'],
            "Date": game['date'],
            "Placements": placements_str
        })
    return pd.DataFrame(history_data)

def recalculate_all_ratings_and_stats():
    """
    Recalculates all player ratings and stats from scratch based on the database history.
    This function now updates the database directly.
    """
    history = db.get_game_history_db()
    history.sort(key=lambda x: datetime.strptime(x['date'], "%Y-%m-%d").date())

    all_players_records = db.get_all_players_db()
    sim_players = {p['name']: Player(
        player_id=p['id'],
        name=p['name'],
        # Reset stats to default before recalculation
        rating=1500, rd=350, volatility=0.06,
        last_played_date=datetime.strptime(p['season_start'], "%Y-%m-%d").date(),
        season_start=datetime.strptime(p['season_start'], "%Y-%m-%d").date(),
        games=0
    ) for p in all_players_records}

    for game in history:
        game_date = datetime.strptime(game['date'], "%Y-%m-%d").date()
        placements_for_processing = []
        game_players_for_processing = []
        for p_name, place in game['placements']:
            if p_name in sim_players:
                player_obj = sim_players[p_name]
                placements_for_processing.append((player_obj, place))
                game_players_for_processing.append(player_obj)
        
        if len(game_players_for_processing) >= 2:
            process_game(game_players_for_processing, placements_for_processing, game_date, save_history=False)
            for p in game_players_for_processing:
                p.games += 1
                p.last_played_date = game_date
    
    # Update all players in the database with the new recalculated stats
    for p in sim_players.values():
        db.update_player_db(p.id, p.rating, p.rd, p.volatility, p.last_played_date, p.games)

def edit_player(old_name, new_name):
    """Edits a player's name in the database."""
    if not old_name or not new_name:
        return "Please select a player and provide a new name.", get_players_df(), *(gr.update(),) * 13

    if db.get_player_by_name_db(new_name):
        return f"Player name '{new_name}' already exists.", get_players_df(), *(gr.update(),) * 13

    if not db.get_player_by_name_db(old_name):
        return f"Player '{old_name}' not found.", get_players_df(), *(gr.update(),) * 13

    db.edit_player_name_db(old_name, new_name)

    updated_player_list = get_player_names()
    dropdown_update = gr.update(choices=updated_player_list, value=None)
    
    return f"Player '{old_name}' has been renamed to '{new_name}'.", get_players_df(), *(dropdown_update,) * 13

def remove_player(name_to_remove):
    """Removes a player from the database and recalculates all ratings."""
    if not name_to_remove:
        return "Please select a player to remove.", get_players_df(), get_game_history_df(), *(gr.update(),) * 13

    db.remove_player_db(name_to_remove)
    
    # After removing the player, we need to recalculate everyone's stats
    recalculate_all_ratings_and_stats()

    updated_player_list = get_player_names()
    dropdown_update = gr.update(choices=updated_player_list, value=None)

    return f"Player '{name_to_remove}' removed and all ratings recalculated.", get_players_df(), get_game_history_df(), *(dropdown_update,) * 13

def delete_match(match_id_to_delete):
    """Deletes a match from the database and re-calculates all ratings."""
    if match_id_to_delete is None or match_id_to_delete == "":
        return "Please enter a match ID to delete.", get_game_history_df(), get_players_df()

    try:
        match_id_int = int(match_id_to_delete)
        db.delete_match_db(match_id_int)
    except (ValueError, TypeError):
        return "Invalid Match ID selected.", get_game_history_df(), get_players_df()
    
    # After deleting the match, recalculate all ratings
    recalculate_all_ratings_and_stats()

    return f"Match {match_id_to_delete} deleted and ratings recalculated.", get_game_history_df(), get_players_df()


# --- Gradio Interface ---

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# MTG Chaos Commander - Glicko-2 Ratings")

    with gr.Tab("Player Management"):
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Current Roster")
                players_df_output = gr.DataFrame(get_players_df, interactive=False)
            with gr.Column(scale=1):
                gr.Markdown("### Add New Player")
                player_name_input = gr.Textbox(label="Player Name")
                player_rating_input = gr.Number(label="Initial Rating", value=1500)
                player_rd_input = gr.Number(label="Initial RD", value=350)
                player_volatility_input = gr.Number(label="Initial Volatility", value=0.06)
                add_player_button = gr.Button("Add Player")
                add_player_status = gr.Textbox(label="Status", interactive=False)

                gr.Markdown("### Edit Player Name")
                edit_player_select = gr.Dropdown(choices=get_player_names(), label="Select Player to Edit")
                new_player_name_input = gr.Textbox(label="New Player Name")
                edit_player_button = gr.Button("Edit Player Name")
                edit_player_status = gr.Textbox(label="Status", interactive=False)

                gr.Markdown("### Remove Player")
                remove_player_select = gr.Dropdown(choices=get_player_names(), label="Select Player to Remove")
                remove_player_button = gr.Button("Remove Player")
                remove_player_status = gr.Textbox(label="Status", interactive=False)

    with gr.Tab("Add Match"):
        gr.Markdown("### Enter Match Details")
        match_date_input = gr.Textbox(label="Match Date (YYYY-MM-DD)", value=datetime.today().strftime("%Y-%m-%d"))
        
        player_names = get_player_names()
        
        # Create a number input to select the number of players
        num_players_input = gr.Number(label="Number of Players", value=4, minimum=2, maximum=10, step=1)

        player_inputs = []
        player_dropdowns = []
        player_columns = []
        # Create a maximum number of player inputs and control their visibility
        for i in range(5): # 5 rows for 10 players
            with gr.Row():
                for j in range(2): # 2 players per row
                    player_idx = i * 2 + j
                    with gr.Column(visible=(player_idx < 4)) as col:
                        dd = gr.Dropdown(player_names, label=f"Player {player_idx + 1}")
                        tb = gr.Textbox(label=f"Placement")
                        player_inputs.extend([dd, tb])
                        player_dropdowns.append(dd)
                        player_columns.append(col)
        
        add_match_button = gr.Button("Submit Match")
        match_status_output = gr.Textbox(label="Match Result", interactive=False)
        match_players_df_output = gr.DataFrame(interactive=False)


    with gr.Tab("Manage Matches"):
        gr.Markdown("### Match History")
        with gr.Row():
            history_df_output = gr.DataFrame(get_game_history_df, interactive=False)
        with gr.Row():
            with gr.Column(scale=1):
                match_id_input = gr.Textbox(label="Match ID to Delete")
                delete_match_button = gr.Button("Delete Selected Match")
            with gr.Column(scale=3):
                delete_status_output = gr.Textbox(label="Status", interactive=False)

    with gr.Tab("Player Stats"):
        gr.Markdown("### View Player Performance")
        stats_player_dropdown = gr.Dropdown(choices=get_player_names(), label="Select Player")
        plot_button = gr.Button("Generate Plots")
        
        with gr.Row():
            rating_plot = gr.Plot(label="Rating")
            rd_plot = gr.Plot(label="Rating Deviation")
            volatility_plot = gr.Plot(label="Volatility")

    # --- Event Handlers ---

    def update_player_inputs(num_players):
        """Updates the visibility of player input fields based on the selected number."""
        updates = []
        num_players = int(num_players)
        for i in range(10):
            updates.append(gr.update(visible=i < num_players))
        return updates

    num_players_input.change(
        fn=update_player_inputs,
        inputs=num_players_input,
        outputs=player_columns
    )

    add_player_button.click(
        fn=add_player,
        inputs=[player_name_input, player_rating_input, player_rd_input, player_volatility_input],
        outputs=[add_player_status, players_df_output] + player_dropdowns + [stats_player_dropdown, edit_player_select, remove_player_select]
    )
    
    add_match_button.click(
        fn=add_match_ui,
        inputs=[match_date_input] + player_inputs,
        outputs=[match_status_output, players_df_output, match_players_df_output, history_df_output]
    )

    plot_button.click(
        fn=plot_player_history,
        inputs=[stats_player_dropdown],
        outputs=[rating_plot, rd_plot, volatility_plot]
    )


    delete_match_button.click(
        fn=delete_match,
        inputs=[match_id_input],
        outputs=[delete_status_output, history_df_output, players_df_output]
    )


    edit_player_button.click(
        fn=edit_player,
        inputs=[edit_player_select, new_player_name_input],
        outputs=[edit_player_status, players_df_output] + player_dropdowns + [stats_player_dropdown, edit_player_select, remove_player_select]
    )

    remove_player_button.click(
        fn=remove_player,
        inputs=[remove_player_select],
        outputs=[remove_player_status, players_df_output, history_df_output] + player_dropdowns + [stats_player_dropdown, edit_player_select, remove_player_select]
    )


def cleanup_old_files():
    """Removes old JSON files if they exist."""
    for f in ["players.json", "game_history.json", "players_backup.json"]:
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    db.setup_database()
    cleanup_old_files()
    demo.launch()