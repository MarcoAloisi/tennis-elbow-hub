import math

def calculate_vertex_scores(stats):
    name = stats['name']
    
    # 1. SERVE POWER
    avg_speed = stats['avg_1st_kmh']
    fastest_speed = stats['fastest_kmh']
    power = ((avg_speed / 200) * 70) + ((fastest_speed / 230) * 30)
    power = min(100, max(0, power))

    # 2. ACCURACY
    first_pct = stats['first_serve_pct']
    df = stats['double_faults']
    # Calculate total service points
    total_service_points = stats['first_serve_points_total'] + stats['second_serve_points_total']
    
    df_penalty_score = 100
    if total_service_points > 0:
        df_penalty_score = 100 - ((df / total_service_points) * 1000)
    
    accuracy = (first_pct * 0.7) + (df_penalty_score * 0.3)
    accuracy = min(100, max(0, accuracy))

    # 3. CONSISTENCY
    winners = stats['winners']
    ue = stats['unforced_errors']
    consistency = 0
    if (winners + ue) > 0:
        consistency = (winners / (winners + ue)) * 100

    # 4. NET GAME
    net_won = stats['net_points_won']
    net_total = stats['net_points_total']
    net_game = 0
    if net_total > 0:
        win_pct = (net_won / net_total) * 100
        # Decay function: win_pct * (1 - e^(-0.1 * approaches))
        volume_factor = 1 - math.exp(-0.1 * net_total)
        net_game = win_pct * volume_factor

    # 5. RALLY
    short_won = stats['short_won']
    short_total = stats['short_total']
    med_won = stats['med_won']
    med_total = stats['med_total']
    long_won = stats['long_won']
    long_total = stats['long_total']
    
    def get_pct(won, total):
        return (won / total * 100) if total > 0 else 0
        
    rally = (get_pct(short_won, short_total) * 0.2) + \
            (get_pct(med_won, med_total) * 0.4) + \
            (get_pct(long_won, long_total) * 0.4)

    # 6. BREAK POINTS
    bp_won = stats['bp_won']
    bp_total = stats['bp_total']
    ret_won = stats['ret_won']
    ret_total = stats['ret_total']
    
    bp_pct = (bp_won / bp_total * 100) if bp_total > 0 else 0
    ret_pct = (ret_won / ret_total * 100) if ret_total > 0 else 0
    
    break_points = (bp_pct * 0.6) + (ret_pct * 0.4)

    return {
        "Serve Power": round(power, 1),
        "Accuracy": round(accuracy, 1),
        "Consistency": round(consistency, 1),
        "Net Game": round(net_game, 1),
        "Rally": round(rally, 1),
        "Break Points": round(break_points, 1)
    }

# Data from Match Log line 6159
# barboza (ELO: 3029) def. Marcolino (ELO: 2171)
barboza_stats = {
    'name': 'Barboza',
    'avg_1st_kmh': 186,
    'fastest_kmh': 205,
    'first_serve_pct': 76, # 78/102
    'double_faults': 0,
    'first_serve_points_total': 78, # Denom of 1st serve won (55/78)
    'second_serve_points_total': 24, # Denom of 2nd serve won (13/24)
    'winners': 70,
    'unforced_errors': 30,
    'net_points_won': 43,
    'net_points_total': 66,
    'short_won': 69, 'short_total': 121,
    'med_won': 35, 'med_total': 61,
    'long_won': 14, 'long_total': 25,
    'bp_won': 6, 'bp_total': 11,
    'ret_won': 50, 'ret_total': 105
}

marcolino_stats = {
    'name': 'Marcolino',
    'avg_1st_kmh': 191,
    'fastest_kmh': 221,
    'first_serve_pct': 64, # 67/105
    'double_faults': 4,
    'first_serve_points_total': 67, # 40/67
    'second_serve_points_total': 38, # 15/38
    'winners': 34,
    'unforced_errors': 17,
    'net_points_won': 1,
    'net_points_total': 3,
    'short_won': 52, 'short_total': 121,
    'med_won': 26, 'med_total': 61,
    'long_won': 11, 'long_total': 25,
    'bp_won': 2, 'bp_total': 10,
    'ret_won': 34, 'ret_total': 102
}

p1_scores = calculate_vertex_scores(barboza_stats)
p2_scores = calculate_vertex_scores(marcolino_stats)

print(f"{'Category':<15} | {'Barboza':<10} | {'Marcolino':<10}")
print("-" * 40)
for category in p1_scores.keys():
    print(f"{category:<15} | {p1_scores[category]:<10} | {p2_scores[category]:<10}")

print("\n\n--- STRATEGIC INSIGHTS ---")

print("\nWHY: Barboza's Net Game (Shape Width)")
print(f"Barboza: {p1_scores['Net Game']} vs Marcolino: {p2_scores['Net Game']}")
print(f"Reason: Barboza approached {barboza_stats['net_points_total']} times (Winning {round(43/66*100)}%). High volume activates the multiplier.")
print(f"Marcolino approached only {marcolino_stats['net_points_total']} times. Even if he won 100%, the volume decay penalty (1 - e^-0.3) would crush his score.")

print("\nWHY: Marcolino's Serve Power")
print(f"Barboza: {p1_scores['Serve Power']} vs Marcolino: {p2_scores['Serve Power']}")
print(f"Reason: Marcolino has a faster Avg ({marcolino_stats['avg_1st_kmh']} vs {barboza_stats['avg_1st_kmh']}) and Peak ({marcolino_stats['fastest_kmh']} vs {barboza_stats['fastest_kmh']}).")

print("\nWIN CONDITION")
print("Barboza: Dominates the Net (65.0) and Short/Med Rallies. Win condition is shortening points by coming forward.")
print("Marcolino: Higher Serve Power (95.7) but loses in Consistency (66.7 vs 70.0). Needs to rely on 'First Strike' tennis to avoid rallies where he is outmatched.")
