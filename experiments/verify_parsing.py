"""Standalone verification of parsing logic without backend dependencies."""

import re

# Sample raw data from user
raw_data = '''0 CCF9 "S.Halep vs PrinceGUE" 1B198F21 190 7B4 38D "XKT v4.2d" "4/4 -- 15:30•" 7F0 2 31 "0010 AO Rod Laver Night" 69767A84 0 F32B "H.Hurkacz vs P.1" 18198F21 12C 7BF 2A7 "XKT v4.2d" "0/0 -- 40:30•" 895 4 1B "0010 AO Rod Laver Night" 69767B44 0 5001 "bencu vs T.Clay" 1A199521 1F4 4B7 256 "XKT v4.2d" "3/1 -- 15:15•" 490 5 33 "00031 Auckland ATP 250" 69767B4A 0 10E1 "Cheroky vs Salva" 1B198EA1 32 3CF 1 "salva aqui" "2/1 -- 40:15•" 3CF 0 0 "BlueGreenCement" 69767B93'''

SERVER_PATTERN = re.compile(
    r'"([^"]*)"'
    r"|"
    r"([0-9A-Fa-f]+)"
    r"|"
    r"(\*)"
    r"|"
    r"([0-9.]+)"
)

def tokenize_server_line(line):
    tokens = []
    for match in SERVER_PATTERN.finditer(line):
        token = match.group(1) or match.group(2) or match.group(3) or match.group(4)
        if token is not None:
            tokens.append(token)
    return tokens

def safe_int_from_hex(value, default=0):
    try:
        return int(value, 16)
    except (ValueError, TypeError):
        return default

def parse_game_info(value):
    """Parse GameInfo bitfield."""
    trial = (value >> 0) & 0x3
    player_cfg = (value >> 2) & 0x7
    nb_set = (value >> 5) & 0x3
    skill_mode = (value >> 7) & 0x3
    
    mode_names = {0: "Singles", 1: "Unknown", 2: "Competitive Doubles", 3: "Cooperative Doubles"}
    set_names = {0: "1 Set", 1: "Best of 3", 2: "Best of 5", 3: "Best of 5"}
    
    return {
        'mode_display': mode_names.get(player_cfg, "Unknown"),
        'sets_display': set_names.get(nb_set, "Unknown"),
        'nb_set': nb_set,
    }

def clean_surface_name(name):
    """Simulate the surface_display property."""
    surface_map = {
        "BlueGreenCement": "Hard Court",
        "Clay": "Clay Court",
        "Grass": "Grass Court",
        "Indoor": "Indoor Hard",
    }
    if name in surface_map:
        return surface_map[name]
    
    name_lower = name.lower()
    if "clay" in name_lower:
        return "Clay Court"
    if "grass" in name_lower:
        return "Grass Court"
    if "indoor" in name_lower:
        return "Indoor Hard"
    
    if re.match(r"^\d+\s+", name):
        if "AO" in name or "Australian" in name:
            return "Hard Court"
        if "Roma" in name:
            return "Clay Court"
        return "Hard Court"
    
    return name

def clean_tournament_name(name):
    """Simulate the tournament_display property."""
    known_surfaces = {"BlueGreenCement", "Clay", "Grass", "Indoor"}
    if name in known_surfaces:
        return ""
    return re.sub(r"^\d+\s+", "", name)

# Parse and display
print("=" * 70)
print("TENNIS ELBOW 4 - LIVE SCORES PARSER VERIFICATION")
print("=" * 70)

all_tokens = tokenize_server_line(raw_data)

# Split into entries
entries = []
current = []

for token in all_tokens:
    is_boundary = token in ("0", "*", "0.0.0.0") or re.match(r"^\d+\.\d+\.\d+\.\d+$", token)
    
    if is_boundary and len(current) >= 14:
        entries.append(current)
        current = [token]
    else:
        current.append(token)

if len(current) >= 14:
    entries.append(current)

print(f"\nParsed {len(entries)} server entries:\n")

for idx, tokens in enumerate(entries):
    if len(tokens) < 14:
        continue
        
    ip = tokens[0]
    port = tokens[1]
    name = tokens[2]
    game_info_hex = tokens[3]
    elo = safe_int_from_hex(tokens[5])
    score = tokens[8]
    other_elo = safe_int_from_hex(tokens[9])
    surface_name = tokens[12]
    
    is_started = ip == "0"
    game_info = parse_game_info(safe_int_from_hex(game_info_hex))
    
    surface_display = clean_surface_name(surface_name)
    tournament = clean_tournament_name(surface_name)
    
    status = "🔴 LIVE" if is_started else "⏳ WAITING"
    
    print(f"[{idx+1}] {status}")
    print(f"    Match: {name}")
    print(f"    ELO: {elo} vs {other_elo}")
    print(f"    Score: {score}")
    print(f"    Format: {game_info['mode_display']} - {game_info['sets_display']}")
    print(f"    Surface: {surface_display}")
    if tournament:
        print(f"    Tournament: {tournament}")
    print()

print("=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
