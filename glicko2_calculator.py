import math
import json
import pandas as pd
from datetime import datetime
from collections import defaultdict
import os

# Glicko-2 Constants
PI_SQUARED = math.pi ** 2
SCALING_FACTOR = 173.7178
EPSILON = 0.000001
MAX_RATING_CHANGE = 250

class Player:
    def __init__(self, name, rating=1500, rd=350, volatility=0.06, last_played_date=None, season_start=None):
        """Initialize a player with Glicko-2 rating parameters."""
        self.name = name
        self.rating = rating
        self.rd = rd
        self.volatility = volatility
        self.last_played_date = last_played_date or season_start or datetime.today().date()
        self.games_today = 0
        self.season_start = season_start or datetime.today().date()

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

def input_date(prompt):
    """Prompt user for a date in YYYY-MM-DD format, default to today if empty."""
    while True:
        try:
            date_str = input(prompt).strip()
            if not date_str:
                return datetime.today().date()
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print("! Invalid date. Use format YYYY-MM-DD. Please try again.")

def input_float(prompt, default_value, min_value=0):
    """Prompt user for a float value, with a default and minimum constraint."""
    while True:
        try:
            value_str = input(prompt).strip()
            if not value_str:
                return default_value
            value = float(value_str)
            if value < min_value:
                print(f"! Value must be at least {min_value}. Please try again.")
                continue
            return value
        except ValueError:
            print("! Invalid number. Please enter a valid number or leave blank for default.")

def load_players(player_file="players.json"):
    """Load player data from a JSON file, return list of Player objects."""
    try:
        with open(player_file, 'r') as f:
            data = json.load(f)
        players = []
        for p in data:
            last_played = datetime.strptime(p['last_played_date'], "%Y-%m-%d").date() if p['last_played_date'] else None
            season_start = datetime.strptime(p['season_start'], "%Y-%m-%d").date() if p['season_start'] else None
            players.append(Player(p['name'], p['rating'], p['rd'], p['volatility'], last_played, season_start))
        return players
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_players(players, player_file="players.json"):
    """Save player data to a JSON file."""
    data = [{
        'name': p.name,
        'rating': p.rating,
        'rd': p.rd,
        'volatility': p.volatility,
        'last_played_date': p.last_played_date.strftime("%Y-%m-%d") if p.last_played_date else None,
        'season_start': p.season_start.strftime("%Y-%m-%d") if p.season_start else None
    } for p in players]
    with open(player_file, 'w') as f:
        json.dump(data, f, indent=4)

def save_game_history(game_date, placements, game_history_file="game_history.json"):
    """Append game results to a JSON file."""
    game_data = {
        'date': game_date.strftime("%Y-%m-%d"),
        'placements': [(p.name, place) for p, place in placements]
    }
    try:
        with open(game_history_file, 'r') as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []
    history.append(game_data)
    with open(game_history_file, 'w') as f:
        json.dump(history, f, indent=4)

def select_players(all_players):
    """Allow user to select players for a game or add new players."""
    selected = []
    while True:
        print("\n=== Current Player Pool ===")
        for i, p in enumerate(all_players, 1):
            print(f"{i}. {p.name} (Rating={p.rating:.1f}, RD={p.rd:.1f}, Vol={p.volatility:.4f})")
        choice = input("Enter player #, 'add' to create a new player, or 'done': ").strip().lower()
        if choice == 'done':
            if len(selected) >= 2:
                break
            print("! Need at least 2 players. Please try again.")
        elif choice == 'add':
            name = input("New player name: ").strip()
            if not name:
                print("! Name cannot be empty. Please try again.")
                continue
            if name in [p.name for p in all_players]:
                print("! Player name already exists. Please choose a unique name.")
                continue
            rating = input_float("Rating (default 1500): ", default_value=1500)
            rd = input_float("RD (default 350): ", default_value=350)
            vol = input_float("Volatility (default 0.06): ", default_value=0.06, min_value=0.0001)
            last_played = input_date("Last played date (YYYY-MM-DD) or leave blank for today: ")
            new_player = Player(name, rating, rd, vol, last_played)
            all_players.append(new_player)
            selected.append(new_player)
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(all_players):
                    if all_players[idx] not in selected:
                        selected.append(all_players[idx])
                    else:
                        print("! Player already selected. Please choose another.")
                else:
                    print("! Invalid number. Please try again.")
            except ValueError:
                print("! Please enter a number, 'add', or 'done'. Please try again.")
    return selected

def input_placements(players):
    """Prompt user to input placements for each player in the game."""
    placements = []
    print("\n=== Enter Placements ===")
    for p in players:
        while True:
            try:
                place = input(f"Placement for {p.name}: ").strip()
                place = int(place)
                if 1 <= place <= len(players):
                    placements.append((p, place))
                    break
                print(f"! Placement must be between 1 and {len(players)}. Please try again.")
            except ValueError:
                print("! Please enter a valid number. Please try again.")
    return placements

def read_game_file(file_path, all_players, dry_run=False):
    """Read and validate game results from a text file."""
    games = []
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"! File {file_path} not found.")
        return []

    for line_num, line in enumerate(lines, 1):
        try:
            parts = [part.strip() for part in line.split(',')]
            if len(parts) < 3:
                print(f"! Line {line_num}: Too few entries. Skipping.")
                continue
            date_str = parts[0]
            try:
                game_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                print(f"! Line {line_num}: Invalid date format ({date_str}). Use YYYY-MM-DD. Skipping.")
                continue

            game_players = []
            placements = []
            for entry in parts[1:]:
                try:
                    name, place = entry.split(':')
                    place = int(place)
                    if place < 1:
                        print(f"! Line {line_num}: Invalid placement ({place}) for {name}. Skipping game.")
                        break
                    player = next((p for p in all_players if p.name == name), None)
                    if not player and not dry_run:
                        print(f"! Line {line_num}: Player {name} not found. Adding with default ratings.")
                        player = Player(name)
                        all_players.append(player)
                    elif not player:
                        print(f"! Line {line_num}: Player {name} not found. Skipping in dry run.")
                        break
                    if player in game_players:
                        print(f"! Line {line_num}: Duplicate player {name}. Skipping game.")
                        break
                    game_players.append(player)
                    placements.append((player, place))
                except (ValueError, IndexError):
                    print(f"! Line {line_num}: Invalid format for {entry}. Use 'name:place'. Skipping game.")
                    break
            else:
                if len(game_players) < 2:
                    print(f"! Line {line_num}: Need at least 2 players. Skipping.")
                    continue
                if max(place for _, place in placements) > len(game_players):
                    print(f"! Line {line_num}: Placements exceed number of players. Skipping.")
                    continue
                games.append((game_date, placements))
        except Exception as e:
            print(f"! Line {line_num}: Error processing line ({str(e)}). Skipping.")
    return games

def display_verification(game_date, placements):
    """Display game details for user verification and allow edits."""
    while True:
        print("\n=== Game Verification ===")
        print(f"Game Date: {game_date}")
        placements_sorted = sorted(placements, key=lambda x: x[1])
        for i, (p, place) in enumerate(placements_sorted, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(place, "   ")
            print(f"{medal} {i}. {p.name} | Place: {place} | Rating: {p.rating:.1f}, RD: {p.rd:.1f}, Vol: {p.volatility:.4f}")
        choice = input("Confirm (y), Cancel (n), or Edit player #: ").strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        elif choice.isdigit():
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(placements_sorted):
                    player_to_edit = placements_sorted[idx][0]
                    while True:
                        try:
                            new_place = input(f"New placement for {player_to_edit.name}: ").strip()
                            new_place = int(new_place)
                            if 1 <= new_place <= len(placements):
                                for i, (p, _) in enumerate(placements):
                                    if p == player_to_edit:
                                        placements[i] = (p, new_place)
                                        break
                                break
                            print(f"! Placement must be between 1 and {len(placements)}. Please try again.")
                        except ValueError:
                            print("! Please enter a valid number. Please try again.")
                else:
                    print("! Invalid player number. Please try again.")
            except ValueError:
                print("! Invalid input. Please enter a number. Please try again.")
        else:
            print("! Invalid input. Please enter 'y', 'n', or a player number. Please try again.")

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
    print(f"Updating {player.name} | Old Vol: {player.volatility:.5f}, E={E}, v={v:.4f}, delta={delta:.4f}")
    new_vol = update_volatility(mu, phi, player.volatility, v, delta)
    print(f"New Vol: {new_vol:.5f}")
    phi_star = math.sqrt(phi**2 + new_vol**2)
    phi_prime = 1 / math.sqrt(1 / phi_star**2 + 1 / v)
    mu_prime = mu + phi_prime**2 * sum(g * (outcome - e) for g, e, outcome in zip(g_phis, E, outcomes))
    delta_cap = MAX_RATING_CHANGE / SCALING_FACTOR * math.sqrt(num_players - 1)
    mu_prime = max(min(mu_prime, mu + delta_cap), mu - delta_cap)
    player.from_glicko2_scale(mu_prime, phi_prime)
    player.volatility = new_vol

def process_game(players, placements, game_date, game_history_file="game_history.json"):
    """Process a multiplayer game, updating player ratings and saving to history."""
    # Count ties at each placement
    tied_at_place = defaultdict(int)
    for _, place in placements:
        tied_at_place[place] += 1

    # Update RD for all players
    for player in players:
        update_rd_for_inactivity(player, game_date)

    # Calculate outcomes for each player
    num_players = len(players)
    outcomes = calculate_outcomes(placements, num_players, tied_at_place)

    # Update ratings for each player
    for player, results in outcomes.items():
        mu, phi = player.to_glicko2_scale()
        is_first_game_today = player.games_today == 0
        update_player_ratings(player, mu, phi, results, is_first_game_today, num_players, tied_at_place, placements)
        player.last_played_date = game_date
        player.games_today += 1

    # Save game to history
    save_game_history(game_date, placements, game_history_file)

def generate_excel_output(games, output_file=None):
    """Generate an Excel file with game results."""
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_file = f"game_results_{timestamp}.xlsx"
    data = []
    for game_date, placements in games:
        row = {'Date': game_date.strftime("%Y-%m-%d")}
        for i, (player, place) in enumerate(sorted(placements, key=lambda x: x[1]), 1):
            row[f'Player_{i}'] = player.name
            row[f'Place_{i}'] = place
            row[f'Rating_{i}'] = round(player.rating, 1)
            row[f'RD_{i}'] = round(player.rd, 1)
            row[f'Vol_{i}'] = round(player.volatility, 4)
        data.append(row)
    df = pd.DataFrame(data)
    df.to_excel(output_file, index=False)
    print(f"Excel file saved as {output_file}")

def display_game_history(game_history_file="game_history.json"):
    """Display game history, optionally filtered by date or player."""
    try:
        with open(game_history_file, 'r') as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("! No game history found.")
        return

    filter_type = input("Filter by (d)ate, (p)layer, or (a)ll: ").strip().lower()
    if filter_type == 'd':
        date_str = input("Enter date (YYYY-MM-DD): ").strip()
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print("! Invalid date format. Showing all games.")
            target_date = None
    elif filter_type == 'p':
        player_name = input("Enter player name: ").strip()
    else:
        filter_type = 'a'

    print("\n=== Game History ===")
    for game in sorted(history, key=lambda x: x['date']):
        game_date = datetime.strptime(game['date'], "%Y-%m-%d").date()
        if filter_type == 'd' and game_date != target_date:
            continue
        if filter_type == 'p' and not any(name == player_name for name, _ in game['placements']):
            continue
        print(f"Date: {game['date']}")
        for i, (name, place) in enumerate(sorted(game['placements'], key=lambda x: x[1]), 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(place, "   ")
            print(f"{medal} {i}. {name}: Place {place}")
        print()

def display_leaderboard(all_players, game_history_file="game_history.json"):
    """Display leaderboard with ratings and stats."""
    try:
        with open(game_history_file, 'r') as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []

    stats = {p.name: {'games': 0, 'wins': 0, 'ties': 0, 'losses': 0} for p in all_players}
    for game in history:
        placements = defaultdict(list)
        for name, place in game['placements']:
            stats[name]['games'] += 1
            placements[place].append(name)
        for place, names in sorted(placements.items()):
            if len(names) > 1:
                for name in names:
                    stats[name]['ties'] += 1
            elif place == 1:
                stats[names[0]]['wins'] += 1
            else:
                stats[names[0]]['losses'] += 1

    print("\n=== Leaderboard ===")
    for p in sorted(all_players, key=lambda x: x.rating, reverse=True):
        rank = sorted(all_players, key=lambda x: x.rating, reverse=True).index(p) + 1
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "   ")
        s = stats.get(p.name, {'games': 0, 'wins': 0, 'ties': 0, 'losses': 0})
        print(f"{medal} {p.name}: Rating={p.rating:.1f}, RD={p.rd:.1f}, Vol={p.volatility:.4f}, "
              f"Games={s['games']}, Wins={s['wins']}, Ties={s['ties']}, Losses={s['losses']}")

def undo_last_game(all_players, player_file="players.json", game_history_file="game_history.json", backup_file="players_backup.json"):
    """Revert the last game by restoring player ratings and reprocessing history."""
    try:
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("! No backup found. Cannot undo.")
        return

    try:
        with open(game_history_file, 'r') as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("! No game history found. Cannot undo.")
        return

    if not history:
        print("! No games to undo.")
        return

    # Restore player ratings from backup
    all_players.clear()
    for p in backup_data:
        last_played = datetime.strptime(p['last_played_date'], "%Y-%m-%d").date() if p['last_played_date'] else None
        season_start = datetime.strptime(p['season_start'], "%Y-%m-%d").date() if p['season_start'] else None
        all_players.append(Player(p['name'], p['rating'], p['rd'], p['volatility'], last_played, season_start))

    # Remove last game from history
    history.pop()
    with open(game_history_file, 'w') as f:
        json.dump(history, f, indent=4)

    # Reprocess remaining games
    for game in history:
        game_date = datetime.strptime(game['date'], "%Y-%m-%d").date()
        placements = []
        for name, place in game['placements']:
            player = next((p for p in all_players if p.name == name), None)
            if player:
                placements.append((player, place))
        if placements:
            process_game([p for p, _ in placements], placements, game_date)

    save_players(all_players)
    print("Last game undone and ratings updated.")

def run_normal_mode():
    """Run the main program loop for managing multiplayer games."""
    print("=== Glicko-2 Tournament Manager ===")
    all_players = load_players()
    season_start = input_date("Enter season start date (YYYY-MM-DD): ")
    for player in all_players:
        player.season_start = season_start

    while True:
        mode = input("\nEnter 'manual', 'file', 'history', 'leaderboard', 'undo', or 'exit': ").strip().lower()
        if mode == 'exit':
            break
        elif mode == 'manual':
            game_date = input_date("Enter game date (YYYY-MM-DD): ")
            game_players = select_players(all_players)
            placements = input_placements(game_players)
            if display_verification(game_date, placements):
                save_players(all_players, "players_backup.json")
                process_game(game_players, placements, game_date)
                print("\n=== Ratings After Game ===")
                for p in sorted(game_players, key=lambda x: x.rating, reverse=True):
                    rank = sorted(game_players, key=lambda x: x.rating, reverse=True).index(p) + 1
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "   ")
                    print(f"{medal} {p.name}: Rating={p.rating:.1f}, RD={p.rd:.1f}, Vol={p.volatility:.4f}")
                save_players(all_players)
                generate_excel_output([(game_date, placements)])
            else:
                print("! Game entry cancelled. Start over.")
        elif mode == 'file':
            file_path = input("Enter path to game file: ").strip()
            dry_run = input("Run in dry run mode? (y/n): ").strip().lower() == 'y'
            games = read_game_file(file_path, all_players, dry_run)
            if not games or dry_run:
                if not dry_run:
                    print("! No valid games to process. Try again.")
                continue
            processed_games = []
            save_players(all_players, "players_backup.json")
            for game_date, placements in games:
                if display_verification(game_date, placements):
                    process_game([p for p, _ in placements], placements, game_date)
                    processed_games.append((game_date, placements))
                    break  # Exit loop after processing one game to avoid re-verification
                else:
                    print(f"! Game on {game_date} cancelled. Skipping.")
                    continue
            if processed_games:
                print("\n=== Final Standings ===")
                game_players = set(p for _, placements in processed_games for p, _ in placements)
                for p in sorted(game_players, key=lambda x: x.rating, reverse=True):
                    rank = sorted(game_players, key=lambda x: x.rating, reverse=True).index(p) + 1
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "   ")
                    print(f"{medal} {p.name}: Rating={p.rating:.1f}, RD={p.rd:.1f}, Vol={p.volatility:.4f}")
                save_players(all_players)
                generate_excel_output(processed_games)
            else:
                print("! No games were processed.")
        elif mode == 'history':
            display_game_history()
        elif mode == 'leaderboard':
            display_leaderboard(all_players)
        elif mode == 'undo':
            undo_last_game(all_players)
        else:
            print("! Invalid mode. Please enter 'manual', 'file', 'history', 'leaderboard', 'undo', or 'exit'.")

def main():
    """Entry point for the Glicko-2 multiplayer rating system."""
    print("Welcome to the Glicko-2 Multiplayer Rating System")
    while True:
        mode = input("Type 'TEST' to run test mode, or press Enter to begin normal use: ").strip().lower()
        if mode in ['test', '']:
            break
        print("! Please enter 'TEST' or press Enter. Please try again.")
    if mode == "test":
        print("Test mode coming soon!")
    else:
        run_normal_mode()

if __name__ == "__main__":
    main()
