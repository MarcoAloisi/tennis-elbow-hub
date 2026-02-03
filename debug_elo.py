
import re

text = "Madferit (ELO: 1095 +30 ; Crc = 16726438) def. Marco (ELO: 1307 -30 ; Crc = 15968142) : 7/5 7/5 - United Cup - 0:35'55 (1:41'43) - 2025-03-19 19:49 [Online]"

# Current Strict Pattern
strict_pattern = re.compile(
    r"(.*?) \(ELO: (.*?)\) def\. (.*?) \(ELO: (.*?)\) : (.*?) - (.*?) - (.*?) - (.*)"
)

match = strict_pattern.match(text)
if match:
    print("Strict Pattern MATCHED")
    groups = match.groups()
    print(f"Group 1 (P1 Name): '{groups[0]}'")
    print(f"Group 2 (P1 ELO): '{groups[1]}'")
    print(f"Group 3 (P2 Name): '{groups[2]}'")
    print(f"Group 4 (P2 ELO): '{groups[3]}'")
    
    # Simulate P2 ELO Extraction
    p2_str = groups[3].strip()
    m = re.match(r"(\d+)", p2_str)
    if m:
        print(f"Extracted P2 ELO: {m.group(1)}")
    else:
        print(f"Failed to extract integer from '{p2_str}'")

else:
    print("Strict Pattern FAILED")
    
    # Fallback simulation
    fallback_pattern = re.compile(r"(.*?) def\. (.*?) : (.*?) - (.*?) - (.*?) - (.*)")
    match = fallback_pattern.match(text)
    if match:
        print("Fallback Pattern MATCHED")
        groups = match.groups()
        raw_p2 = groups[1].strip()
        print(f"Raw P2: '{raw_p2}'")
        
        p2_elo_match = re.search(r"\(ELO:\s*(\d+)", raw_p2)
        if p2_elo_match:
            print(f"Fallback Extracted P2 ELO: {p2_elo_match.group(1)}")
        else:
             print("Fallback Failed to extract ELO")
    else:
        print("Fallback Pattern FAILED")
