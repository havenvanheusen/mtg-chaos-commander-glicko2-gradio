import math
from datetime import datetime
from collections import defaultdict

# Glicko-2 Constants
PI_SQUARED = math.pi ** 2
SCALING_FACTOR = 173.7178
EPSILON = 0.000001
MAX_RATING_CHANGE = 250

class Player:
    def __init__(self, name, rating=1500, rd=350, volatility=0.06, season_start=None):
        self.name = name
        self.rating = rating
        self.rd = rd
        self.volatility = volatility
        self.last_played_date = None
        self.games_today = 0
        self.season_start = season_start or datetime.today().date()

    def to_glicko2_scale(self):
        return (self.rating - 1500) / SCALING_FACTOR, self.rd / SCALING_FACTOR

    def from_glicko2_scale(self, mu, phi):
        self.rating = mu * SCALING_FACTOR + 1500
        self.rd = phi * SCALING_FACTOR

def glicko2_g(phi):
    return 1 / math.sqrt(1 + 3 * phi**2 / PI_SQUARED)

def update_volatility(player, v, delta, tau=0.5):
    a = math.log(player.volatility ** 2)
    x0 = a
    while True:
        d = player.phi**2 + v + math.exp(x0)
        h1 = -(x0 - a) / (tau**2) - 0.5 * math.exp(x0) / d + 0.5 * math.exp(x0) * (delta / d)**2
        h2 = -1 / (tau**2) - 0.5 * math.exp(x0) * (player.phi**2 + v) / (d**2) + 0.5 * delta**2 * math.exp(x0) * (player.phi**2 + v - math.exp(x0)) / (d**3)
        x1 = x0 - h1 / h2
        if abs(x1 - x0) < EPSILON:
            break
        x0 = x1
    return math.exp(x1 / 2)

def validate_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print("! Invalid date format. Please use YYYY-MM-DD.")
        return None

def input_with_validation(prompt, validation_func, error_msg):
    while True:
        user_input = input(prompt)
        validated = validation_func(user_input)
        if validated is not None:
            return validated
        print(f"! {error_msg}")

def select_players(all_players):
    selected = []
    while True:
        print("\n=== Current Player Pool ===")
        for i, p in enumerate(all_players, 1):
            print(f"{i:>2}. {p.name} (Rating={p.rating:.1f}, RD={p.rd:.1f})")
        
        choice = input("\nEnter NUMBER, 'add', or 'done': ").strip().lower()
        
        if choice == 'done':
            if len(selected) >= 2:
                break
            print("! Need at least 2 players.")
        elif choice == 'add':
            name = input("New player name: ").strip()
            rating = input_with_validation(
                "Rating (default 1500): ",
                lambda x: float(x) if x else 1500,
                "Invalid number. Using 1500."
            )
            rd = input_with_validation(
                "RD (default 350): ",
                lambda x: float(x) if x else 350,
                "Invalid number. Using 350."
            )
            vol = input_with_validation(
                "Volatility (default 0.06): ",
                lambda x: float(x) if x else 0.06,
                "Invalid number. Using 0.06."
            )
            new_player = Player(name, rating, rd, vol, all_players[0].season_start if all_players else None)
            all_players.append(new_player)
            selected.append(new_player)
            print(f"> Added {name}")
        else:
            try:
                idx = int(choice.split('.')[0]) - 1
                if 0 <= idx < len(all_players):
                    selected.append(all_players[idx])
                    print(f"> Selected {all_players[idx].name}")
                else:
                    print("! Invalid number")
            except ValueError:
                print("! Please enter: number, 'add', or 'done'")
    return selected

def input_placements(players):
    placement_groups = defaultdict(list)
    print("\n=== Enter Placements ===")
    print("For ties: Enter the same placement number")
    print("Example: Two players sharing 2nd place both get '2'")
    
    for player in players:
        while True:
            try:
                place = int(input(f"Placement for {player.name}: "))
                if 1 <= place <= len(players):
                    placement_groups[place].append(player)
                    break
                print(f"! Must be between 1-{len(players)}")
            except ValueError:
                print("! Numbers only")
    
    # Convert to scored placements with identical scores for ties
    min_place = min(placement_groups.keys())
    max_place = max(placement_groups.keys())
    scored_placements = []
    
    for place, tied_players in sorted(placement_groups.items()):
        if len(placement_groups) == 1:  # All tied
            score = 0.5
        else:
            normalized = (place - min_place) / (max_place - min_place)
            score = 1 - normalized ** 0.7
        
        for player in tied_players:
            scored_placements.append((player, score, place))
    
    return scored_placements

def process_game(players, placements, game_date):
    # Reset daily counters for new day
    for p in players:
        if p.last_played_date != game_date:
            p.games_today = 0
    
    # Group by placement for tie handling
    placement_groups = defaultdict(list)
    for player, score, place in placements:
        placement_groups[place].append((player, score))
    
    # First pass: calculate all updates
    updates = {}
    for place, group in sorted(placement_groups.items()):
        for player, score in group:
            # Time decay
            reference_date = player.last_played_date or player.season_start
            days_passed = (game_date - reference_date).days
            weeks_passed = days_passed // 7
            
            if weeks_passed > 0 and player.last_played_date is not None:
                player.rd = min(math.sqrt(player.rd**2 + 
                               (player.volatility**2) * weeks_passed), 350)

            mu, phi = player.to_glicko2_scale()
            player.phi = phi

            # Calculate results against all opponents
            results = []
            for opp, _, _ in placements:
                if opp != player:
                    opp_mu, opp_phi = opp.to_glicko2_scale()
                    results.append((opp_mu, opp_phi, score))
            
            # Store updates to apply later
            updates[player] = (mu, phi, results, player.games_today == 0)

    # Second pass: apply updates
    for player, (mu, phi, results, is_first_game_today) in updates.items():
        if is_first_game_today:
            # Full Glicko-2 update
            opp_mus, opp_phis, outcomes = zip(*results)
            g_phis = [glicko2_g(phi) for phi in opp_phis]
            E = [1 / (1 + math.exp(-g * (mu - opp_mu))) for g, opp_mu in zip(g_phis, opp_mus)]
            v = 1 / sum(g**2 * e * (1 - e) for g, e in zip(g_phis, E))
            delta = v * sum(g * (outcome - e) for g, e, outcome in zip(g_phis, E, outcomes))

            new_volatility = update_volatility(player, v, delta)
            phi_star = math.sqrt(phi**2 + player.volatility**2)
            phi_prime = 1 / math.sqrt(1 / phi_star**2 + 1 / v)
            mu_prime = mu + phi_prime**2 * sum(g * (outcome - e) for g, e, outcome in zip(g_phis, E, outcomes))

            if player.last_played_date is None:  # First game ever
                mu_prime = max(min(mu_prime, mu + MAX_RATING_CHANGE/SCALING_FACTOR), 
                              mu - MAX_RATING_CHANGE/SCALING_FACTOR)

            player.from_glicko2_scale(mu_prime, phi_prime)
            player.volatility = new_volatility
        else:
            # Rating-only update
            for opp_mu, opp_phi, outcome in results:
                g_phi = glicko2_g(opp_phi)
                E = 1 / (1 + math.exp(-g_phi * (mu - opp_mu)))
                mu += (player.rd / SCALING_FACTOR)**2 * g_phi * (outcome - E)
            
            player.from_glicko2_scale(mu, phi)
        
        player.last_played_date = game_date
        player.games_today += 1

    # Third pass: enforce ties
    for place, group in placement_groups.items():
        if len(group) > 1:  # We have a tie
            tied_players = [player for player, _ in group]
            # Average the ratings and RDs
            avg_rating = sum(p.rating for p in tied_players) / len(tied_players)
            avg_rd = sum(p.rd for p in tied_players) / len(tied_players)
            for player in tied_players:
                player.rating = avg_rating
                player.rd = avg_rd

    # Final pass: order RDs by placement
    placements_sorted = sorted(placements, key=lambda x: x[2])
    if len(placements) > 1:
        min_rd = min(p.rd for p in players)
        max_rd = max(p.rd for p in players)
        rd_step = (max_rd - min_rd) / (len(players) - 1)
        
        for i, (player, _, place) in enumerate(placements_sorted):
            # Only adjust if not tied (ties already handled)
            if len(placement_groups[place]) == 1:
                player.rd = min_rd + i * rd_step * 0.7

def main():
    print("=== Glicko-2 Tournament Manager ===")
    
    # Season setup
    season_start = input_with_validation(
        "Enter season start date (YYYY-MM-DD): ",
        validate_date,
        "Invalid date. Using today."
    ) or datetime.today().date()
    
    all_players = []
    
    while True:  # Game loop
        print("\n=== New Game Setup ===")
        game_date = input_with_validation(
            "Game date (YYYY-MM-DD): ",
            validate_date,
            "Invalid date. Try again."
        )
        
        game_players = select_players(all_players)
        placements = input_placements(game_players)
        process_game(game_players, placements, game_date)
        
        # Update global player list
        for p in game_players:
            if p not in all_players:
                p.season_start = season_start
                all_players.append(p)
        
        # Display results
        print("\n=== Updated Ratings ===")
        print(f"Game Date: {game_date}")
        
        # Group by placement for display
        display_groups = defaultdict(list)
        for player, _, place in placements:
            display_groups[place].append(player)
        
        # Display with medals and proper ties
        display_place = 1
        for place in sorted(display_groups.keys()):
            tied_players = display_groups[place]
            medal = ""
            if display_place == 1: medal = "🥇 "
            elif display_place == 2: medal = "🥈 "
            elif display_place == 3: medal = "🥉 "
            
            for player in tied_players:
                print(f"{medal}{display_place}. {player.name}: Rating={player.rating:.1f}, RD={player.rd:.1f}, Vol={player.volatility:.4f}")
            
            display_place += len(tied_players)
        
        if input("\nAdd another game? (y/n): ").lower() != 'y':
            break

if __name__ == "__main__":
    main()
