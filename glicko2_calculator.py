import math
from datetime import datetime
from collections import defaultdict
import random

# Glicko-2 Constants
PI_SQUARED = math.pi ** 2
SCALING_FACTOR = 173.7178
EPSILON = 0.000001
MAX_RATING_CHANGE = 250
MIN_RD = 30
MAX_RD = 350
VOLATILITY_MIN = 0.03
VOLATILITY_MAX = 0.15
DEFAULT_TAU = {'1v1': 0.3, 'multiplayer': 0.5}

class Player:
    def __init__(self, name, rating=1500, rd=350, volatility=0.06, season_start=None):
        self.name = name
        self.rating = rating
        self.rd = min(max(rd, MIN_RD), MAX_RD)
        self.volatility = min(max(volatility, VOLATILITY_MIN), VOLATILITY_MAX)
        self.last_played_date = None
        self.games_today = 0
        self.season_start = season_start or datetime.today().date()

    def to_glicko2_scale(self):
        return (self.rating - 1500) / SCALING_FACTOR, self.rd / SCALING_FACTOR

    def from_glicko2_scale(self, mu, phi):
        self.rating = mu * SCALING_FACTOR + 1500
        self.rd = min(max(phi * SCALING_FACTOR, MIN_RD), MAX_RD)

def glicko2_g(phi):
    return 1 / math.sqrt(1 + 3 * phi**2 / PI_SQUARED)

def update_volatility(player, phi, v, delta):
    tau = DEFAULT_TAU['1v1'] if isinstance(player, Player) and hasattr(player, 'tau') else DEFAULT_TAU['multiplayer']
    a = math.log(player.volatility ** 2)
    x0 = a
    
    while True:
        d = phi**2 + v + math.exp(x0)
        h1 = -(x0 - a) / (tau**2) - 0.5 * math.exp(x0) / d + 0.5 * math.exp(x0) * (delta / d)**2
        h2 = -1 / (tau**2) - 0.5 * math.exp(x0) * (phi**2 + v) / (d**2) + 0.5 * delta**2 * math.exp(x0) * (phi**2 + v - math.exp(x0)) / (d**3)
        x1 = x0 - h1 / h2
        
        if abs(x1 - x0) < EPSILON:
            break
        x0 = x1
    
    return min(max(math.exp(x1 / 2), VOLATILITY_MIN), VOLATILITY_MAX)

def process_game(players, placements, game_date):
    game_type = '1v1' if len(players) == 2 else 'multiplayer'
    
    # Reset daily counters
    for p in players:
        if p.last_played_date != game_date:
            p.games_today = 0
    
    # Time decay adjustment
    for p in players:
        if p.last_played_date is not None:
            days_passed = (game_date - p.last_played_date).days
            if days_passed > 0:
                p.rd = min(math.sqrt(p.rd**2 + (p.volatility**2) * days_passed), MAX_RD)
        
        # Accelerate RD decay for high-RD 1v1
        if game_type == '1v1' and p.rd > 200:
            p.rd = min(p.rd * 0.9, 200)

    # Main rating updates
    updates = {}
    placement_groups = defaultdict(list)
    
    for player, score, place in placements:
        placement_groups[place].append((player, score))
        mu, phi = player.to_glicko2_scale()
        results = []
        
        for opp, _, _ in placements:
            if opp != player:
                opp_mu, opp_phi = opp.to_glicko2_scale()
                results.append((opp_mu, opp_phi, score))
        
        updates[player] = (mu, phi, results, player.games_today == 0)

    # Apply updates
    for player, (mu, phi, results, is_first_game) in updates.items():
        if is_first_game:
            opp_mus, opp_phis, outcomes = zip(*results)
            g_phis = [glicko2_g(phi) for phi in opp_phis]
            E = [1 / (1 + math.exp(-g * (mu - opp_mu))) for g, opp_mu in zip(g_phis, opp_mus)]
            v = 1 / sum(g**2 * e * (1 - e) for g, e in zip(g_phis, E))
            delta = v * sum(g * (outcome - e) for g, e, outcome in zip(g_phis, E, outcomes))

            new_volatility = update_volatility(player, phi, v, delta)
            phi_star = math.sqrt(phi**2 + new_volatility**2)
            phi_prime = 1 / math.sqrt(1 / phi_star**2 + 1 / v)
            mu_prime = mu + phi_prime**2 * sum(g * (outcome - e) for g, e, outcome in zip(g_phis, E, outcomes))

            if player.last_played_date is None:
                mu_prime = max(min(mu_prime, mu + MAX_RATING_CHANGE/SCALING_FACTOR),
                              mu - MAX_RATING_CHANGE/SCALING_FACTOR)

            player.from_glicko2_scale(mu_prime, phi_prime)
            player.volatility = new_volatility
        else:
            for opp_mu, opp_phi, outcome in results:
                g_phi = glicko2_g(opp_phi)
                E = 1 / (1 + math.exp(-g_phi * (mu - opp_mu)))
                mu += (player.rd / SCALING_FACTOR)**2 * g_phi * (outcome - E)
            
            player.from_glicko2_scale(mu, phi)

        player.last_played_date = game_date
        player.games_today += 1

    # Handle ties
    for place, group in placement_groups.items():
        if len(group) > 1:
            tied_players = [player for player, _ in group]
            avg_rating = sum(p.rating for p in tied_players) / len(tied_players)
            avg_rd = sum(p.rd for p in tied_players) / len(tied_players)
            
            for player in tied_players:
                player.rating = avg_rating
                player.rd = avg_rd

def simulate_season():
    players = [Player(f"Player_{i}") for i in range(1, 101)]
    start_date = datetime(2025, 1, 1)
    
    for week in range(1, 11):
        current_date = start_date + timedelta(weeks=week)
        print(f"\n=== Week {week} ===")
        
        # Simulate 5 concurrent games per week
        for game_num in range(1, 6):
            num_players = random.choice([2, 3, 4, 5])
            game_players = random.sample(players, num_players)
            placements = []
            
            for place in range(1, num_players + 1):
                score = 1.0 - (place-1)/num_players
                placements.append((game_players[place-1], score, place))
            
            # Random tie (20% chance)
            if random.random() < 0.2 and num_players > 2:
                tie_place = random.randint(2, num_players)
                placements[tie_place-1] = (placements[tie_place-1][0], 
                                         placements[tie_place-2][1], 
                                         placements[tie_place-2][2])
            
            process_game(game_players, placements, current_date)
        
        # Print leaderboard
        top_players = sorted(players, key=lambda x: (-x.rating, x.rd))[:5]
        for i, p in enumerate(top_players, 1):
            print(f"{i}. {p.name}: {p.rating:.1f}±{p.rd:.1f} (σ={p.volatility:.3f})")

if __name__ == "__main__":
    simulate_season()
