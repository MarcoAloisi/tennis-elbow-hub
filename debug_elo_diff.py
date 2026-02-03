
import re

text = "Madferit (ELO: 1095 +30 ; Crc = 16726438) def. Marco (ELO: 1307 -30 ; Crc = 15968142) : 7/5 7/5 - United Cup - 0:35'55 (1:41'43) - 2025-03-19 19:49 [Online]"

# Updated Strict Pattern from analyzer.py
strict_pattern = re.compile(
    r"(.*?) \(ELO: (.*?)\) def\. (.*?) \(ELO: (.*?)\)\s*:\s*(.*?) - (.*?) - (.*?) - (.*)"
)

match = strict_pattern.match(text)
if match:
    print("Strict Pattern MATCHED")
    groups = match.groups()
    p1_elo_group = groups[1].strip()
    p2_elo_group = groups[3].strip()
    
    print(f"Group 1 (P1 ELO String): '{p1_elo_group}'")
    print(f"Group 3 (P2 ELO String): '{p2_elo_group}'")
    
    # Test P1 Extraction Logic
    print("\nTesting P1 Extraction:")
    m1 = re.match(r"(\d+)(?:\s*([+-]\d+))?", p1_elo_group)
    if m1:
        print(f"  ELO: {m1.group(1)}")
        print(f"  Diff: {m1.group(2)}")
    else:
        print("  NO MATCH")

    # Test P2 Extraction Logic
    print("\nTesting P2 Extraction:")
    m2 = re.match(r"(\d+)(?:\s*([+-]\d+))?", p2_elo_group)
    if m2:
        print(f"  ELO: {m2.group(1)}")
        print(f"  Diff: {m2.group(2)}")
    else:
        print("  NO MATCH")

else:
    print("Strict Pattern FAILED")
