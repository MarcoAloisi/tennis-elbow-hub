"""Debug the empty string tokenization issue."""

import re

# The problematic entry with empty TagLine
test_data = '0.0.0.0 10E1 "Player 1" 1B198F41 64 0 0 "" "..." 0 0 0 "BlueGreenCement" 697681AD'

SERVER_PATTERN = re.compile(
    r'"([^"]*)"'  # Quoted strings
    r"|"
    r"([0-9A-Fa-f]+)"  # Hex values
    r"|"
    r"(\*)"  # Asterisk marker
    r"|"
    r"([0-9.]+)"  # IP-like values
)

print("=" * 60)
print("CURRENT TOKENIZER (BUGGY)")
print("=" * 60)

def tokenize_buggy(line):
    tokens = []
    for match in SERVER_PATTERN.finditer(line):
        # BUG: Empty string "" is falsy, so it falls through!
        token = match.group(1) or match.group(2) or match.group(3) or match.group(4)
        if token is not None:
            tokens.append(token)
    return tokens

tokens_buggy = tokenize_buggy(test_data)
print(f"Token count: {len(tokens_buggy)} (expected 14)")
print("Tokens:")
for i, t in enumerate(tokens_buggy):
    print(f"  [{i:2}] {repr(t)}")

print("\n" + "=" * 60)
print("FIXED TOKENIZER")
print("=" * 60)

def tokenize_fixed(line):
    tokens = []
    for match in SERVER_PATTERN.finditer(line):
        # FIX: Check each group explicitly, handle empty strings properly
        if match.group(1) is not None:  # Quoted string (can be empty)
            tokens.append(match.group(1))
        elif match.group(2) is not None:  # Hex value
            tokens.append(match.group(2))
        elif match.group(3) is not None:  # Asterisk
            tokens.append(match.group(3))
        elif match.group(4) is not None:  # IP-like
            tokens.append(match.group(4))
    return tokens

tokens_fixed = tokenize_fixed(test_data)
print(f"Token count: {len(tokens_fixed)} (expected 14)")
print("Tokens:")
for i, t in enumerate(tokens_fixed):
    print(f"  [{i:2}] {repr(t)}")

print("\n" + "=" * 60)
print("FIELD MAPPING CHECK")
print("=" * 60)

expected_fields = [
    "IP", "Port", "Name", "GameInfo", "MaxPing", "Elo", "NbGame",
    "TagLine", "Score", "OtherElo", "GiveUpRate", "Reputation",
    "SurfaceName", "CreationTime"
]

print("\nBuggy tokenizer field mapping:")
for i, field in enumerate(expected_fields):
    if i < len(tokens_buggy):
        print(f"  {field:15}: {repr(tokens_buggy[i])}")
    else:
        print(f"  {field:15}: MISSING!")

print("\nFixed tokenizer field mapping:")
for i, field in enumerate(expected_fields):
    if i < len(tokens_fixed):
        print(f"  {field:15}: {repr(tokens_fixed[i])}")
    else:
        print(f"  {field:15}: MISSING!")

# Also verify NbSet parsing
print("\n" + "=" * 60)
print("NbSet PARSING CHECK")
print("=" * 60)

game_info_values = [
    ("18198F21", "H.Hurkacz vs P.1"),
    ("1A199521", "L.Love vs V.Arkride"),
    ("1B198F41", "Player 1"),
    ("8199462", "(4) Squeaky"),
]

def parse_nb_set(hex_val):
    val = int(hex_val, 16)
    nb_set = (val >> 5) & 0x3
    return nb_set

for hex_val, name in game_info_values:
    nb_set = parse_nb_set(hex_val)
    set_names = {0: "1 Set", 1: "Best of 3", 2: "Best of 5", 3: "Best of 5"}
    print(f"  {name:25} GameInfo=0x{hex_val} nb_set={nb_set} -> {set_names.get(nb_set)}")
