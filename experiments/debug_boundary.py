"""Comprehensive debug to find the actual parsing issue."""

import re

# Test with the ACTUAL current data that shows in screenshot
# Looking at screenshot, it shows WAITING entries with "10E1", "F32B" etc as names
# Let's trace through the EXACT parsing

raw_data = '''0 F32B "H.Hurkacz vs P.1" 18198F21 12C 7BF 2A7 "XKT v4.2d" "4/3 -- •40:Ad" 8A7 4 1B "0010 AO Rod Laver Night" 69767FCC 0.0.0.0 10E1 "Player 1" 1B198F41 64 0 0 "" "..." 0 0 0 "BlueGreenCement" 697681AD'''

SERVER_PATTERN = re.compile(
    r'"([^"]*)"'  # Quoted strings
    r"|"
    r"([0-9A-Fa-f]+)"  # Hex values
    r"|"
    r"(\*)"  # Asterisk marker
    r"|"
    r"([0-9.]+)"  # IP-like values
)

def tokenize_fixed(line):
    tokens = []
    for match in SERVER_PATTERN.finditer(line):
        if match.group(1) is not None:
            tokens.append(match.group(1))
        elif match.group(2) is not None:
            tokens.append(match.group(2))
        elif match.group(3) is not None:
            tokens.append(match.group(3))
        elif match.group(4) is not None:
            tokens.append(match.group(4))
    return tokens

all_tokens = tokenize_fixed(raw_data)

print("=" * 70)
print("ALL TOKENS")
print("=" * 70)
for i, t in enumerate(all_tokens):
    print(f"[{i:2}] {repr(t)}")

print("\n" + "=" * 70)
print("BOUNDARY DETECTION TRACE")
print("=" * 70)

current_tokens = []
entries = []

for i, token in enumerate(all_tokens):
    is_boundary = (
        token in ("0", "*", "0.0.0.0")
        or re.match(r"^\d+\.\d+\.\d+\.\d+$", token) is not None
        or (
            current_tokens
            and len(current_tokens) >= 14
            and re.match(r"^[0-9A-Fa-f]+$", token)
            and i + 1 < len(all_tokens)
        )
    )
    
    print(f"[{i:2}] {repr(token):25} boundary={is_boundary} current_len={len(current_tokens)}")
    
    if is_boundary and current_tokens and len(current_tokens) >= 14:
        print(f"     >> SPLIT! Entry {len(entries)+1} has {len(current_tokens)} tokens")
        entries.append(current_tokens)
        current_tokens = [token]
    else:
        current_tokens.append(token)

if len(current_tokens) >= 14:
    print(f"     >> FINAL! Entry {len(entries)+1} has {len(current_tokens)} tokens")
    entries.append(current_tokens)

print("\n" + "=" * 70)
print("PARSED ENTRIES")
print("=" * 70)

for idx, tokens in enumerate(entries):
    print(f"\n--- Entry {idx+1} ({len(tokens)} tokens) ---")
    print(f"  [0] IP:        {tokens[0]}")
    print(f"  [1] Port:      {tokens[1]}")
    print(f"  [2] Name:      {tokens[2]}")  # THIS SHOULD BE THE PLAYER NAME!
    print(f"  [5] Elo:       {tokens[5]} = {int(tokens[5], 16)} decimal")
    print(f"  [7] TagLine:   {repr(tokens[7])}")
    print(f"  [8] Score:     {tokens[8]}")
    print(f"  [12] Surface:  {tokens[12]}")

print("\n" + "=" * 70)
print("DIAGNOSIS")
print("=" * 70)

# Check if we're getting the right tokens
entry1 = entries[0] if entries else []
entry2 = entries[1] if len(entries) > 1 else []

if entry1:
    print(f"\nEntry 1 match_name = {repr(entry1[2])}")
    if entry1[2] == "H.Hurkacz vs P.1":
        print("  ✅ Entry 1 name is CORRECT")
    else:
        print(f"  ❌ Entry 1 name is WRONG! Expected 'H.Hurkacz vs P.1'")

if entry2:
    print(f"\nEntry 2 match_name = {repr(entry2[2])}")
    if entry2[2] == "Player 1":
        print("  ✅ Entry 2 name is CORRECT")
    else:
        print(f"  ❌ Entry 2 name is WRONG! Expected 'Player 1'")
