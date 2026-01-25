"""Debug the actual parsing with the latest data to find the issue."""

import re

# Latest raw data
raw_data = '''0 10E1 "FaKy vs Darek" 1B198E41 12C 100 19 "XKT v4.2d" "..." 0 0 0 "0013 Italian Open" 69769000'''

# The CURRENT regex pattern from the parser
SERVER_PATTERN = re.compile(
    r'"([^"]*)"'  # Quoted strings - GROUP 1
    r"|"
    r"([0-9A-Fa-f]+)"  # Hex values - GROUP 2
    r"|"
    r"(\*)"  # Asterisk marker - GROUP 3
    r"|"
    r"([0-9.]+)"  # IP-like values - GROUP 4
)

print("=" * 70)
print("REGEX MATCHING ANALYSIS")
print("=" * 70)

print("\nRaw data:", raw_data[:80], "...")
print("\nMatching each token:")

for i, match in enumerate(SERVER_PATTERN.finditer(raw_data)):
    g1 = match.group(1)
    g2 = match.group(2)
    g3 = match.group(3)
    g4 = match.group(4)
    
    matched_text = match.group(0)
    
    if g1 is not None:
        which = "G1 (quoted)"
    elif g2 is not None:
        which = "G2 (hex)"
    elif g3 is not None:
        which = "G3 (asterisk)"
    elif g4 is not None:
        which = "G4 (IP)"
    else:
        which = "NONE!"
    
    print(f"  [{i:2}] {which:15} = {repr(matched_text):30}")

print("\n" + "=" * 70)
print("TOKENIZATION WITH FIXED tokenizer_server_line")
print("=" * 70)

def tokenize_fixed(line):
    tokens = []
    for match in SERVER_PATTERN.finditer(line):
        if match.group(1) is not None:  # Quoted string (can be empty)
            tokens.append(match.group(1))
        elif match.group(2) is not None:  # Hex value
            tokens.append(match.group(2))
        elif match.group(3) is not None:  # Asterisk
            tokens.append(match.group(3))
        elif match.group(4) is not None:  # IP-like
            tokens.append(match.group(4))
    return tokens

tokens = tokenize_fixed(raw_data)
print(f"\nToken count: {len(tokens)} (expected 14)")

expected_fields = [
    "IP", "Port", "Name", "GameInfo", "MaxPing", "Elo", "NbGame",
    "TagLine", "Score", "OtherElo", "GiveUpRate", "Reputation",
    "SurfaceName", "CreationTime"
]

for i, field in enumerate(expected_fields):
    if i < len(tokens):
        print(f"  [{i:2}] {field:15}: {repr(tokens[i])}")
    else:
        print(f"  [{i:2}] {field:15}: MISSING!")

print("\n" + "=" * 70)
print("CHECKING THE ISSUE: Regex group priority")
print("=" * 70)

# The issue might be that "0" gets matched by BOTH group 2 (hex) AND group 4 (IP-like)
# Let's check which one wins

test_values = ["0", "0.0.0.0", "10E1", "192.168.1.1"]
for val in test_values:
    match = SERVER_PATTERN.match(val)
    if match:
        g1, g2, g3, g4 = match.group(1), match.group(2), match.group(3), match.group(4)
        print(f"  '{val}': g1={g1}, g2={g2}, g3={g3}, g4={g4}")
    else:
        print(f"  '{val}': NO MATCH")

print("\n" + "=" * 70)
print("PROBLEM ANALYSIS")
print("=" * 70)

print("""
Looking at the regex pattern order:
  1. Quoted strings: "..."
  2. Hex values: [0-9A-Fa-f]+
  3. Asterisk: *
  4. IP-like: [0-9.]+

ISSUE: "0" matches BOTH group 2 (hex) AND group 4 (IP-like).
Since group 2 comes first in the pattern, "0" is captured as HEX, not as IP!

This means when we check for boundaries with token == "0", it should still work
because we're just comparing the value.

But... let me check if the quoted strings with just numbers are the issue...
""")

# Test with a problematic pattern - what if the data has no proper quotes?
print("Testing edge cases:")
weird_data = '0 10E1 FaKy 1234'  # No quotes around name
print(f"\nData without quotes: {weird_data}")
tokens_weird = tokenize_fixed(weird_data)
print(f"Tokens: {tokens_weird}")
