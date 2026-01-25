"""Debug script to analyze the actual raw data from Tennis Elbow 4."""

import re

# Actual raw data from the user
raw_data = '''0 CCF9 "S.Halep vs PrinceGUE" 1B198F21 190 7B4 38D "XKT v4.2d" "4/4 -- 15:30•" 7F0 2 31 "0010 AO Rod Laver Night" 69767A84 0 F32B "H.Hurkacz vs P.1" 18198F21 12C 7BF 2A7 "XKT v4.2d" "0/0 -- 40:30•" 895 4 1B "0010 AO Rod Laver Night" 69767B44 0 5001 "bencu vs T.Clay" 1A199521 1F4 4B7 256 "XKT v4.2d" "3/1 -- 15:15•" 490 5 33 "00031 Auckland ATP 250" 69767B4A 0 10E1 "Cheroky vs Salva" 1B198EA1 32 3CF 1 "salva aqui" "2/1 -- 40:15•" 3CF 0 0 "BlueGreenCement" 69767B93 0 A5A3 "Ilios vs MeezyGunshot" 1B198EA1 12C 347 24 "XKT v4.2d" "4/0 -- •30:30" 31B 6 1C "0010 AO Rod Laver Night" 69767C09 0.0.0.0 10E1 "Louis Love" 1A199521 1F4 6C0 494 "XKT v4.2d" "..." 293 6 FFFFFFFFFFFFFFE9 "0009 AO Rod Laver Day" 69767CBC 0.0.0.0 10E1 "ElCharli0214800" 18198F21 12C 293 2E "XKT v4.2d" "..." 0 2 4A "0047 Roma ATP 1000" 69767CFB * 5 0 0 32B 36C346 0 MG-on'''

SERVER_PATTERN = re.compile(
    r'"([^"]*)"'  # Quoted strings
    r"|"
    r"([0-9A-Fa-f]+)"  # Hex values
    r"|"
    r"(\*)"  # Asterisk marker
    r"|"
    r"([0-9.]+)"  # IP-like values
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
    games_per_set = (value >> 18) & 0x7
    control_mode = (value >> 22) & 0x3
    preview = (value >> 24) & 0x7
    tiredness = bool((value >> 27) & 0x1)
    
    mode_names = {0: "Singles", 2: "Competitive Doubles", 3: "Cooperative Doubles"}
    set_names = {0: "1 Set", 1: "Best of 3", 2: "Best of 5", 3: "Best of 5"}
    
    return {
        'trial': trial,
        'player_config': player_cfg,
        'mode_display': mode_names.get(player_cfg, "Unknown"),
        'nb_set': nb_set,
        'sets_display': set_names.get(nb_set, "Unknown"),
        'skill_mode': skill_mode,
        'games_per_set': games_per_set,
        'control_mode': control_mode,
        'tiredness': tiredness
    }

print("=" * 80)
print("TOKENIZING RAW DATA")
print("=" * 80)

all_tokens = tokenize_server_line(raw_data)
print("Total tokens:", len(all_tokens))
print("\nTokens:")
for i, t in enumerate(all_tokens):
    print("  [{:3}] {}".format(i, repr(t)))

print("\n" + "=" * 80)
print("PARSING INDIVIDUAL SERVER ENTRIES")
print("=" * 80)

# Expected format per entry (14 tokens):
# 0: IP, 1: Port, 2: Name, 3: GameInfo, 4: MaxPing, 5: Elo, 6: NbGame
# 7: TagLine, 8: Score, 9: OtherElo, 10: GiveUpRate, 11: Reputation
# 12: SurfaceName, 13: CreationTime

# Split by boundary markers
entries = []
current = []

for i, token in enumerate(all_tokens):
    is_boundary = (
        token in ("0", "*", "0.0.0.0") or
        re.match(r"^\d+\.\d+\.\d+\.\d+$", token) is not None
    )
    
    if is_boundary and len(current) >= 14:
        entries.append(current)
        current = [token]
    else:
        current.append(token)

if len(current) >= 14:
    entries.append(current)

print("\nFound {} server entries:".format(len(entries)))
print("-" * 80)

for idx, tokens in enumerate(entries):
    print("\n[Entry {}] Token count: {}".format(idx + 1, len(tokens)))
    
    if len(tokens) >= 14:
        ip = tokens[0]
        port = tokens[1]
        name = tokens[2]
        game_info_hex = tokens[3]
        max_ping = safe_int_from_hex(tokens[4])
        elo = safe_int_from_hex(tokens[5])
        nb_game = safe_int_from_hex(tokens[6])
        tag_line = tokens[7]
        score = tokens[8]
        other_elo = safe_int_from_hex(tokens[9])
        give_up_rate = safe_int_from_hex(tokens[10])
        reputation = safe_int_from_hex(tokens[11])
        surface_name = tokens[12]
        creation_time = safe_int_from_hex(tokens[13])
        
        is_started = ip == "0"
        game_info = parse_game_info(safe_int_from_hex(game_info_hex))
        
        print("  Status:     {}".format("LIVE" if is_started else "WAITING"))
        print("  IP:         {}".format(ip))
        print("  Port:       {} (0x{})".format(safe_int_from_hex(port), port))
        print("  Name:       {}".format(name))
        print("  Elo:        {} (0x{})".format(elo, tokens[5]))
        print("  Other Elo:  {} (0x{})".format(other_elo, tokens[9]))
        print("  Score:      {}".format(score))
        print("  TagLine:    {}".format(tag_line))
        print("  Surface:    {}".format(surface_name))
        print("  Sets:       {} (nb_set={})".format(game_info['sets_display'], game_info['nb_set']))
        print("  Mode:       {}".format(game_info['mode_display']))
    else:
        print("  INCOMPLETE ENTRY: {}".format(tokens[:5]))

print("\n" + "=" * 80)
print("ISSUES IDENTIFIED")
print("=" * 80)

print("""
1. SURFACE NAME FORMAT:
   The 'SurfaceName' field contains tournament identifiers like:
   - "0010 AO Rod Laver Night" (Australian Open Rod Laver Arena Night Session)
   - "00031 Auckland ATP 250"
   - "BlueGreenCement" (actual court surface)
   
   The numeric prefixes (0010, 00031, 0009, 0047) appear to be court/tournament codes.
   Need to either:
   a) Clean these up for display, OR
   b) Extract the actual surface type separately

2. SETS DISPLAY:
   The GameInfo bitfield contains nb_set which indicates:
   - 0 = 1 Set
   - 1 = Best of 3
   - 2 = Best of 5
   
   This should be displayed in the UI.

3. SPECIAL MARKER ENTRY:
   The data contains a special entry: '* 5 0 0 32B 36C346 0 MG-on'
   This appears to be metadata (maybe "ManaGames-online" indicator?)
   and should be filtered out.
""")
