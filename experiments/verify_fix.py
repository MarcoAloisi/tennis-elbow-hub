"""Verify the fixed regex pattern works correctly."""

import re

# The FIXED regex pattern
SERVER_PATTERN = re.compile(
    r'"([^"]*)"'  # Group 1: Quoted strings (including empty)
    r"|"
    r"(\d+\.\d+\.\d+\.\d+)"  # Group 2: Full IP addresses (must be before hex!)
    r"|"
    r"([0-9A-Fa-f]+)"  # Group 3: Hex values
    r"|"
    r"(\*)"  # Group 4: Asterisk marker
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

print("=" * 60)
print("TESTING FIXED REGEX PATTERN")
print("=" * 60)

# Test 1: IP address parsing
test1 = "0.0.0.0 10E1 \"Player1\""
tokens1 = tokenize_fixed(test1)
print(f"\nTest 1: {test1}")
print(f"Tokens: {tokens1}")
print(f"✅ PASS" if tokens1 == ['0.0.0.0', '10E1', 'Player1'] else f"❌ FAIL - expected ['0.0.0.0', '10E1', 'Player1']")

# Test 2: Empty tagline
test2 = '0 10E1 "Player1" 12345678 64 0 0 "" "..." 0 0 0 "Surface" 12345'
tokens2 = tokenize_fixed(test2)
print(f"\nTest 2: Empty TagLine")
print(f"Token count: {len(tokens2)} (expected 14)")
print(f"Token[7] (TagLine): {repr(tokens2[7])} (expected '')")
print(f"✅ PASS" if len(tokens2) == 14 and tokens2[7] == '' else "❌ FAIL")

# Test 3: Full WAITING entry
test3 = '0.0.0.0 10E1 "Player 1" 1B198F41 64 0 0 "" "..." 0 0 0 "BlueGreenCement" 697681AD'
tokens3 = tokenize_fixed(test3)
print(f"\nTest 3: Full WAITING entry with 0.0.0.0 and empty TagLine")
print(f"Token count: {len(tokens3)} (expected 14)")
print(f"Token[0] (IP): {tokens3[0]} (expected '0.0.0.0')")
print(f"Token[1] (Port): {tokens3[1]} (expected '10E1')")
print(f"Token[2] (Name): {tokens3[2]} (expected 'Player 1')")
print(f"Token[7] (TagLine): {repr(tokens3[7])} (expected '')")
print(f"✅ PASS" if len(tokens3) == 14 and tokens3[0] == '0.0.0.0' and tokens3[2] == 'Player 1' else "❌ FAIL")

# Test 4: Multiple entries
test4 = '0 10E1 "FaKy vs Darek" 1B198E41 12C 100 19 "XKT v4.2d" "..." 0 0 0 "Italian Open" 69769000 0.0.0.0 10E1 "Player 1" 1B198F41 64 0 0 "" "..." 0 0 0 "BlueGreenCement" 697681AD'
tokens4 = tokenize_fixed(test4)
print(f"\nTest 4: Multiple entries")
print(f"Total tokens: {len(tokens4)} (expected 28 = 14*2)")

# Simulate boundary detection
entries = []
current = []
for i, token in enumerate(tokens4):
    is_boundary = (
        token in ("0", "*", "0.0.0.0")
        or re.match(r"^\d+\.\d+\.\d+\.\d+$", token)
    )
    if is_boundary and len(current) >= 14:
        entries.append(current)
        current = [token]
    else:
        current.append(token)
if len(current) >= 14:
    entries.append(current)
    
print(f"Parsed {len(entries)} entries")
for i, entry in enumerate(entries):
    print(f"  Entry {i+1}: {entry[2]} (tokens: {len(entry)})")

print("\n" + "=" * 60)
print("ALL TESTS PASSED!" if all([
    tokens1 == ['0.0.0.0', '10E1', 'Player1'],
    len(tokens2) == 14 and tokens2[7] == '',
    len(tokens3) == 14 and tokens3[2] == 'Player 1',
]) else "SOME TESTS FAILED!")
print("=" * 60)
