import gradio as gr
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import json
from collections import defaultdict

# It's better to import specific functions and classes
# to avoid cluttering the namespace and for clarity.
from glicko2_calculator import (
    Player,
    load_players,
    save_players,
    process_game,
    load_game_history, # Assuming this function will be created to fetch history
    update_rd_for_inactivity 
)

# --- Data Loading and State Management ---

def get_player_names():
    """Returns a list of player names."""
    players = load_players()
    return [p.name for p in players]

def get_players_df():
    """Returns a pandas DataFrame of the current players."""
    players = load_players()
    player_data = {
        "Name": [p.name for p in players],
        "Rating": [round(p.rating, 2) for p in players],
        "RD": [round(p.rd, 2) for p in players],
        "Volatility": [round(p.volatility, 4) for p in players],
        "Last Played": [p.last_played_date.strftime("%Y-%m-%d") if p.last_played_date else "N/A" for p in players]
    }
    return pd.DataFrame(player_data)

# --- GUI Functions ---

def add_player(name, rating, rd, volatility):
    """Adds a new player to the roster and updates dropdowns."""
    players = load_players()

    if not name:
        status = "Player name cannot be empty."
        # status, df, 10 match dd, 1 stats dd, 1 edit dd, 1 remove dd
        return (status, get_players_df()) + (gr.update(),) * 13

    if name in [p.name for p in players]:
        status = f"Player '{name}' already exists."
        return (status, get_players_df()) + (gr.update(),) * 13

    new_player = Player(name, float(rating), float(rd), float(volatility))
    players.append(new_player)
    save_players(players)

    status = f"Player '{name}' added successfully."
    updated_player_list = [p.name for p in players]
    dropdown_update = gr.update(choices=updated_player_list)

    return (status, get_players_df()) + (dropdown_update,) * 13

def add_match_ui(match_date_str, *player_data):
    """Processes a match from the UI and updates ratings."""
    try:
        game_date = datetime.strptime(match_date_str, "%Y-%m-%d").date()
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD.", get_players_df(), None, get_game_history_df()

    all_players = load_players()
    placements = []
    
    # player_data is a list of (player_name, placement) tuples
    num_players_in_match = len(player_data) // 2
    for i in range(num_players_in_match):
        player_name = player_data[i*2]
        placement_str = player_data[i*2 + 1]
        
        if player_name and placement_str:
            try:
                placement = int(placement_str)
                player = next((p for p in all_players if p.name == player_name), None)
                if player:
                    placements.append((player, placement))
            except (ValueError, StopIteration):
                return f"Invalid data for player or placement.", get_players_df(), None, get_game_history_df()

    if len(placements) < 2:
        return "A match must have at least 2 players.", get_players_df(), None, get_game_history_df()

    game_players = [p for p, _ in placements]

    # Check for duplicate players
    if len(game_players) != len(set(p.name for p in game_players)):
        return "Error: A player cannot be entered more than once in the same match.", get_players_df(), None, get_game_history_df()
    
    # Create a backup before processing
    save_players(all_players, "players_backup.json")
    
    # Process the game
    process_game(game_players, placements, game_date)
    
    # Update player stats
    for p in game_players:
        p.games += 1
    
    # Save the updated player data
    save_players(all_players)
    
    # Create a simple results summary
    results_summary = f"Match on {game_date} processed.\n\nNew Ratings:\n"
    for p in sorted(game_players, key=lambda x: x.rating, reverse=True):
        results_summary += f"- {p.name}: {p.rating:.2f} (RD: {p.rd:.2f})\n"

    return results_summary, get_players_df(), get_players_df(), get_game_history_df()


def plot_player_history(player_name):
    """Plots the rating, RD, and volatility history for a selected player."""
    if not player_name:
        return None, None, None

    history = load_game_history()
    if not history:
        return None, None, None

    # Sort history chronologically
    history.sort(key=lambda x: datetime.strptime(x['date'], "%Y-%m-%d").date())

    # Get all unique player names from history
    all_player_names = set()
    for game in history:
        for name, _ in game['placements']:
            all_player_names.add(name)

    # Create a fresh set of player objects for simulation
    sim_players = {name: Player(name) for name in all_player_names}

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
            process_game(game_players_for_processing, placements_for_processing, game_date)

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
    """Returns a pandas DataFrame of the game history."""
    history = load_game_history()
    if not history:
        return pd.DataFrame(columns=["Match ID", "Date", "Placements"])

    history.sort(key=lambda x: datetime.strptime(x['date'], "%Y-%m-%d").date(), reverse=True)
    
    history_data = []
    for i, game in enumerate(history):
        placements_str = ", ".join([f"{p[0]} ({p[1]})" for p in sorted(game['placements'], key=lambda x: x[1])])
        history_data.append({
            "Match ID": i,
            "Date": game['date'],
            "Placements": placements_str
        })
    return pd.DataFrame(history_data)

def recalculate_all_ratings_and_stats(history):
    """
    Given a game history, recalculates all player ratings and stats from scratch.
    Returns the final list of player objects.
    """
    history.sort(key=lambda x: datetime.strptime(x['date'], "%Y-%m-%d").date())

    all_player_names = set()
    for game in history:
        for name, _ in game['placements']:
            all_player_names.add(name)

    sim_players = {name: Player(name) for name in all_player_names}

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
            # Update stats
            for p in game_players_for_processing:
                p.games += 1
    
    return list(sim_players.values())

def edit_player(old_name, new_name):
    """Edits a player's name and updates it across the system."""
    if not old_name or not new_name:
        return "Please select a player and provide a new name.", get_players_df(), (gr.update(),) * 13

    players = load_players()
    
    if new_name in [p.name for p in players if p.name != old_name]:
        return f"Player name '{new_name}' already exists.", get_players_df(), (gr.update(),) * 13

    player_to_edit = next((p for p in players if p.name == old_name), None)
    if not player_to_edit:
        return f"Player '{old_name}' not found.", get_players_df(), (gr.update(),) * 13

    # Update player name in the player list
    player_to_edit.name = new_name
    save_players(players)

    # Update player name in the game history
    history = load_game_history()
    for game in history:
        for i, (name, place) in enumerate(game['placements']):
            if name == old_name:
                game['placements'][i] = (new_name, place)
    
    with open("game_history.json", 'w') as f:
        json.dump(history, f, indent=4)

    updated_player_list = [p.name for p in players]
    dropdown_update = gr.update(choices=updated_player_list, value=None)
    
    return f"Player '{old_name}' has been renamed to '{new_name}'.", get_players_df(), (dropdown_update,) * 13

def remove_player(name_to_remove):
    """Removes a player and recalculates all ratings and stats."""
    if not name_to_remove:
        return "Please select a player to remove.", get_players_df(), get_game_history_df(), *(gr.update(),) * 13

    # Remove player from players.json first
    players = load_players()
    players = [p for p in players if p.name != name_to_remove]
    save_players(players)

    history = load_game_history()
    new_history = []
    for game in history:
        game['placements'] = [(name, place) for name, place in game['placements'] if name != name_to_remove]
        if len(game['placements']) >= 2:
            new_history.append(game)

    final_players = recalculate_all_ratings_and_stats(new_history)
    save_players(final_players)

    with open("game_history.json", 'w') as f:
        new_history.sort(key=lambda x: datetime.strptime(x['date'], "%Y-%m-%d").date(), reverse=False)
        json.dump(new_history, f, indent=4)

    updated_player_list = [p.name for p in final_players]
    dropdown_update = gr.update(choices=updated_player_list, value=None)

    return f"Player '{name_to_remove}' removed and all ratings recalculated.", get_players_df(), get_game_history_df(), *(dropdown_update,) * 13

def delete_match(match_id_to_delete):
    """Deletes a match and re-calculates all ratings."""
    if match_id_to_delete is None:
        return "Please select a match to delete.", get_game_history_df(), get_players_df()

    history = load_game_history()
    history.sort(key=lambda x: datetime.strptime(x['date'], "%Y-%m-%d").date(), reverse=True)

    try:
        match_id_int = int(match_id_to_delete)
        if not (0 <= match_id_int < len(history)):
            raise ValueError
        history.pop(match_id_int)
    except (ValueError, TypeError):
        return "Invalid Match ID selected.", get_game_history_df(), get_players_df()

    final_players = recalculate_all_ratings_and_stats(history)
    save_players(final_players)
    
    with open("game_history.json", 'w') as f:
        history.sort(key=lambda x: datetime.strptime(x['date'], "%Y-%m-%d").date(), reverse=False)
        json.dump(history, f, indent=4)

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


if __name__ == "__main__":
    demo.launch()