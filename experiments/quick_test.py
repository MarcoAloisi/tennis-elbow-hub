"""Quick test to find the specific issue."""

import re

# Test specifically the 0.0.0.0 case
test = "0.0.0.0"
ip_pattern = re.compile(r"([0-9.]+)")
ip_match = re.compile(r"^\d+\.\d+\.\d+\.\d+$")

print("Testing 0.0.0.0:")
print(f"  Pattern [0-9.]+ matches: {ip_pattern.match(test)}")
print(f"  Full IP pattern matches: {ip_match.match(test)}")
print(f"  In tuple check: {test in ('0', '*', '0.0.0.0')}")

# CRITICAL: Test what happens with the SERVER_PATTERN 
SERVER_PATTERN = re.compile(
    r'"([^"]*)"'
    r"|"
    r"([0-9A-Fa-f]+)" 
    r"|"
    r"(\*)"
    r"|"
    r"([0-9.]+)"
)

match = SERVER_PATTERN.match("0.0.0.0")
if match:
    print(f"\nSERVER_PATTERN match for '0.0.0.0':")
    print(f"  Group 1 (quoted): {match.group(1)}")
    print(f"  Group 2 (hex): {match.group(2)}")
    print(f"  Group 3 (asterisk): {match.group(3)}")  
    print(f"  Group 4 (IP): {match.group(4)}")

# The issue: [0-9A-Fa-f]+ matches "0", then we're left with ".0.0.0"
# Let me verify
data = "0.0.0.0 10E1 \"Test\""
print(f"\nTokenizing: {data}")
for i, m in enumerate(SERVER_PATTERN.finditer(data)):
    g = m.group(0)
    print(f"  Match {i}: {repr(g)}")
    
# AH HA! The issue might be that 0.0.0.0 gets split into multiple matches!
# "0" matches hex, then ".0.0.0" or parts of it match separately
print("\n" + "=" * 50)
print("TOKENIZATION TEST")
print("=" * 50)

def tokenize(line):
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

tokens = tokenize("0.0.0.0 10E1 \"Player1\"")
print(f"Tokens: {tokens}")
print(f"Token count: {len(tokens)}")

# If tokens is ['0', '0', '0', '0', '10E1', 'Player1'] then we have a problem!
# Because 0.0.0.0 would be split into 4 separate "0" tokens
