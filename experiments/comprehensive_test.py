"""COMPREHENSIVE PARSER VERIFICATION with latest user data."""

import re

# Latest raw data from user
raw_data = '''0.0.0.0 10E1 "Player 1" 1B198F41 64 0 0 "" "..." 0 0 0 "BlueGreenCement" 697681AD 0 10E1 "(.Squeaky vs TennisStar" 8199462 1F4 87A E6F "XKT(WTSL) v4.3b" "6/1 1/0 -- 0:0•" 61D 4 4A "0010 AO Rod Laver Night" 697681E3 0 10E1 "ElCharli0214800 vs Javicm1988" 18198F21 12C 285 2F "XKT v4.2d" "4/5 -- 40:40•" 2EE 4 4A "0047 Roma ATP 1000" 69768554 0 10E1 "cocoollbg vs mazigh" 1A198F21 12C 2DB 22B "XKT v4.2d" "1/5 -- •15:15" 57B 4 10 "0054 RG Philippe Chatrier Night" 69768563 0 4282 "MeezyGunshot vs Shyfrancy2009" 1B198EA1 12C 2FA A "XKT v4.2d" "4/3 -- •40:Ad" 293 A 3 "0" 697685B5 0 10E1 "Debuffy vs Dani21" 1A199561 12C B52 4F9 "XKT v4.2d" "4/2 -- •15:15" A49 2 50 "0010 AO Rod Laver Night" 6976867A 0 10E1 "Shomyle vs NewEngRF" 1A198F21 12C 83E 57D "XKT v4.2d" "4/1 -- 15:15•" 6A6 A 30 "0013 Montpellier ATP 250" 697686F5 0 10E1 "GregoryDuViveir. vs l.goatic" 1A199521 1F4 577 1C0 "XKT v4.2d" "2/3 -- 15:40•" 59F 12 7 "0009 AO Rod Laver Day" 69768738 0 122D "Kete-15 vs andrefsp1906" 1A198E41 12C 3DC 3D "XKT v4.2d" "0/0 -- •40:40" 3A1 2 26 "0047 Roma ATP 1000" 697687B6 0 10E1 "JorgeCas vs S.Halep" 1A198F21 1F4 6EF 36A "XKT v4.2d" "0/1 -- •30:0" 7C0 2 4B "0013 Montpellier ATP 250" 69768849 0.0.0.0 10E1 "Xnate" 1A198F21 12C 411 71 "XKT v4.2d" "..." 0 1 64 "0009 AO Rod Laver Day" 69768861 0 10E1 "Vaya vs fakefederer" A199562 12C 744 318 "XKT v4.2d" "0/1 -- •0:0" 8FC 2 31 "0010 AO Rod Laver Night" 69768864 0.0.0.0 10E1 "The Big E" 1B198F21 1F4 85B 154 "XKT v4.2d" "..." 899 7 21 "0053 RG Philippe Chatrier Day" 697688A3 0.0.0.0 623 "Player 1" 1B198F22 12C 899 294 "XKT v4.2d" "..." 0 5 17 "0053 RG Philippe Chatrier Day" 697688DD * A 0 0 2E9 36C5B9 0 MG-on'''

# The FIXED regex pattern (IP before hex, handles empty strings)
SERVER_PATTERN = re.compile(
    r'"([^"]*)"'  # Group 1: Quoted strings (including empty)
    r"|"
    r"(\d+\.\d+\.\d+\.\d+)"  # Group 2: Full IP addresses (must be before hex!)
    r"|"
    r"([0-9A-Fa-f]+)"  # Group 3: Hex values
    r"|"
    r"(\*)"  # Group 4: Asterisk marker
)

def tokenize(line):
    """Fixed tokenizer."""
    tokens = []
    for match in SERVER_PATTERN.finditer(line):
        if match.group(1) is not None:  # Quoted string (can be empty "")
            tokens.append(match.group(1))
        elif match.group(2) is not None:  # Full IP address
            tokens.append(match.group(2))
        elif match.group(3) is not None:  # Hex value
            tokens.append(match.group(3))
        elif match.group(4) is not None:  # Asterisk marker
            tokens.append(match.group(4))
    return tokens

def safe_int_from_hex(value, default=0):
    try:
        return int(value, 16)
    except (ValueError, TypeError):
        return default

def parse_game_info(value):
    """Parse GameInfo bitfield according to spec."""
    trial = (value >> 0) & 0x3        # 2 bits
    player_cfg = (value >> 2) & 0x7    # 3 bits
    nb_set = (value >> 5) & 0x3        # 2 bits
    skill_mode = (value >> 7) & 0x3    # 2 bits
    # bits 9-17 are empty (9 bits)
    games_per_set = (value >> 18) & 0x7  # 3 bits
    # bit 21 unused
    control_mode = (value >> 22) & 0x3   # 2 bits
    preview = (value >> 24) & 0x7        # 3 bits
    tiredness = (value >> 27) & 0x1      # 1 bit
    
    mode_map = {0: "Singles", 2: "Competitive Doubles", 3: "Cooperative Doubles"}
    set_map = {0: "1 Set", 1: "Best of 3", 2: "Best of 5", 3: "Best of 5"}
    
    return {
        'mode': mode_map.get(player_cfg, f"Unknown({player_cfg})"),
        'sets': set_map.get(nb_set, f"Unknown({nb_set})"),
        'nb_set': nb_set,
        'player_cfg': player_cfg,
    }

def clean_tournament(name):
    """Clean tournament name - remove numeric prefix."""
    return re.sub(r"^\d+\s+", "", name)

# Tokenize all
print("=" * 80)
print("COMPREHENSIVE PARSER VERIFICATION")
print("=" * 80)

all_tokens = tokenize(raw_data)
print(f"\nTotal tokens: {len(all_tokens)}")

# Split into entries
entries = []
current = []

for i, token in enumerate(all_tokens):
    is_boundary = (
        token in ("0", "*")
        or re.match(r"^\d+\.\d+\.\d+\.\d+$", token) is not None
    )
    
    if is_boundary and len(current) >= 14:
        entries.append(current)
        current = [token]
    else:
        current.append(token)

if len(current) >= 14:
    entries.append(current)

print(f"Parsed entries: {len(entries)}")

# Display all entries
print("\n" + "=" * 80)
print("PARSED SERVER ENTRIES")
print("=" * 80)

all_valid = True
for idx, tokens in enumerate(entries):
    if len(tokens) < 14:
        print(f"\n[{idx+1}] ❌ INCOMPLETE ({len(tokens)} tokens)")
        all_valid = False
        continue
    
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
    give_up = safe_int_from_hex(tokens[10])
    reputation = safe_int_from_hex(tokens[11])
    surface = tokens[12]
    creation = tokens[13]
    
    is_live = ip == "0"
    game_info = parse_game_info(safe_int_from_hex(game_info_hex))
    tournament = clean_tournament(surface)
    
    status = "🔴 LIVE" if is_live else "⏳ WAIT"
    
    # Validation checks
    name_valid = len(name) > 0 and not name.isalnum()  # Names should have spaces or special chars
    elo_valid = 0 <= elo <= 10000  # ELO in reasonable range
    
    print(f"\n[{idx+1}] {status} | {name}")
    print(f"     Port: {port} | ELO: {elo} vs {other_elo}")
    print(f"     Score: {score} | Games: {nb_game}")
    print(f"     Format: {game_info['mode']} - {game_info['sets']}")
    print(f"     Tournament: {tournament}")
    
    # Check for common issues
    if port == name:
        print(f"     ⚠️  WARNING: Name equals Port - possible parsing issue!")
        all_valid = False
    if elo > 100000:
        print(f"     ⚠️  WARNING: ELO suspiciously high - possible parsing issue!")
        all_valid = False

print("\n" + "=" * 80)
print("VERIFICATION RESULTS")
print("=" * 80)

# Specific validations
validations = [
    ("Entry 1 is WAITING (IP=0.0.0.0)", entries[0][0] == "0.0.0.0" if entries else False),
    ("Entry 1 name is 'Player 1'", entries[0][2] == "Player 1" if entries else False),
    ("Entry 1 TagLine is empty ''", entries[0][7] == "" if entries else False),
    ("Entry 2 is LIVE (IP=0)", entries[1][0] == "0" if len(entries) > 1 else False),
    ("Entry 2 name contains 'Squeaky'", "Squeaky" in entries[1][2] if len(entries) > 1 else False),
]

print("\nSpecific Checks:")
for desc, passed in validations:
    print(f"  {'✅' if passed else '❌'} {desc}")

# Count entries by type
live_count = sum(1 for e in entries if e[0] == "0")
wait_count = sum(1 for e in entries if e[0] != "0" and e[0] != "*")
print(f"\nEntry counts: {live_count} LIVE, {wait_count} WAITING")

# Final verdict
print("\n" + "=" * 80)
if all_valid and all(p for _, p in validations):
    print("✅ ALL CHECKS PASSED - PARSER IS WORKING CORRECTLY!")
else:
    print("❌ SOME CHECKS FAILED - REVIEW OUTPUT ABOVE")
print("=" * 80)
