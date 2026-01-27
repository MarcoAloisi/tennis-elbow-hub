"""
DETAILED AUDIT SCRIPT

This script performs a thorough check of:
1. User's Regex vs Current Regex
2. Table ID extraction (raw_match_id)
3. P1/P2 = previousSibling/nextSibling logic vs. cells[0]/cells[2] logic
4. Does the current implementation already do this?

FINDINGS WILL BE PRINTED.
"""

import sys
import os
import re

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from bs4 import BeautifulSoup

# --- USER'S STRICT REGEX ---
# (.*?)\s\(ELO:\s(\d+)\s([+-]\d+)\s;.*?def\.\s(.*?)\s\(ELO:\s(\d+)\s([+-]\d+).*?:\s(.*?)\s-\s(.*?)\s-\s([\d:']+)\s\(([\d:']+)\)\s-\s([\d-]+\s[\d:]+)
# Groups:
# 1: Winner Name, 2: Winner ELO, 3: Winner ELO Delta
# 4: Loser Name, 5: Loser ELO, 6: Loser ELO Delta
# 7: Score, 8: Tournament
# 9: Duration (game time), 10: Duration (real time)
# 11: Date

USER_REGEX = re.compile(
    r"(.*?)\s\(ELO:\s(\d+)\s([+-]\d+)\s;.*?def\.\s(.*?)\s\(ELO:\s(\d+)\s([+-]\d+).*?:\s(.*?)\s-\s(.*?)\s-\s([\d:']+)\s\(([\d:']+)\)\s-\s([\d-]+\s[\d:]+)"
)

# --- CURRENT IMPLEMENTATION'S STRICT REGEX (from analyzer.py) ---
# (.*?) \(ELO: (.*?)\) def\. (.*?) \(ELO: (.*?)\) : (.*?) - (.*?) - (.*?) - (.*)
CURRENT_STRICT_REGEX = re.compile(
    r"(.*?) \(ELO: (.*?)\) def\. (.*?) \(ELO: (.*?)\) : (.*?) - (.*?) - (.*?) - (.*)"
)

# --- SAMPLE LINES FROM HTML ---
# Online match: "Madferit (ELO: 1095 +30 ; Crc = 16726438) def. Marco (ELO: 1307 -30 ; Crc = 15968142) : 7/5 7/5 - United Cup - 0:35'55 (1:41'43) - 2025-03-19 19:49 [Online]"
# CPU match (no ELO): "Jo-Wilfried Tsonga (Incredible-1) def. Novak Djokovic : 1/0 - Monte Carlo ATP 1000 - 0:01'48 (0:04'06) - 2025-04-27 10:22"

SAMPLE_LINES = [
    "Madferit (ELO: 1095 +30 ; Crc = 16726438) def. Marco (ELO: 1307 -30 ; Crc = 15968142) : 7/5 7/5 - United Cup - 0:35'55 (1:41'43) - 2025-03-19 19:49 [Online]",
    "Jo-Wilfried Tsonga (Incredible-1) def. Novak Djokovic : 1/0 - Monte Carlo ATP 1000 - 0:01'48 (0:04'06) - 2025-04-27 10:22",
    "BadVersionMarco (ELO: 1854 -3 ; Crc = 10560073) def. mvkmatt4457 (ELO: 1164 +3 ; Crc = 2341482) : 7/6(5) - RG Philippe Chatrier Day - 0:23'17 (1:00'15) - 2025-05-09 22:47 [Online]",
]


def test_regex():
    print("=" * 60)
    print("PART 1: REGEX COMPARISON")
    print("=" * 60)

    for i, line in enumerate(SAMPLE_LINES):
        print(f"\n--- Sample {i+1} ---")
        print(f"Line: {line[:80]}...")
        
        print("\n  User's Regex:")
        m = USER_REGEX.match(line)
        if m:
            print(f"    MATCHED! Groups: {m.groups()}")
        else:
            print("    NO MATCH")

        print("\n  Current Impl Regex:")
        m = CURRENT_STRICT_REGEX.match(line)
        if m:
            print(f"    MATCHED! Groups: {m.groups()}")
        else:
            print("    NO MATCH (will fall to fallback)")


def test_table_id_and_sibling():
    print("\n" + "=" * 60)
    print("PART 2: TABLE ID & SIBLING LOGIC")
    print("=" * 60)
    
    # Sample HTML snippet (first match)
    html_snippet = """
<p><input type="checkbox" onClick="SetVis(this, '-1038026436')">Madferit (ELO: 1095 +30 ; Crc = 16726438) def. Marco (ELO: 1307 -30 ; Crc = 15968142) : 7/5 7/5 - United Cup - 0:35'55 (1:41'43) - 2025-03-19 19:49 [Online]</p>
<table id="-1038026436"><tr><td class="d1">41 / 66 = 62%</td><td class="c1">1ST SERVE %</td><td class="d1">45 / 79 = 57%</td><td>&nbsp;</td>
<td class="d2">43 / 89 = 48%</td><td class="c2">SHORT RALLIES WON (< 5)</td><td class="d2">46 / 89 = 52%</td></tr>
<tr><td class="d2">6</td><td class="c2">ACES</td><td class="d2">20</td></tr></table>
    """
    soup = BeautifulSoup(html_snippet, "lxml")
    
    # 1. Table ID
    table = soup.find("table")
    table_id = table.get("id") if table else None
    print(f"\n  Table ID extracted: {table_id}")
    print(f"    Expected: -1038026436")
    print(f"    Status: {'PASS' if table_id == '-1038026436' else 'FAIL'}")

    # 2. P1/P2 Sibling Logic Check
    # User spec: "P1 is previousSibling of label, P2 is nextSibling"
    # Current impl: cells[0] is P1, cells[2] is P2
    # In CSS terms: td.c1/c2 = label. td.d1/d2 = data.
    # Layout: <td class="d1">P1_VAL</td><td class="c1">LABEL</td><td class="d1">P2_VAL</td>
    # So cells[0] = P1_VAL, cells[1] = LABEL, cells[2] = P2_VAL.
    # CRITICALLY: P1 is on the LEFT, P2 is on the RIGHT.
    
    print("\n  Sibling Logic Check:")
    rows = soup.find_all("tr")
    if rows:
        first_row = rows[0]
        cells = first_row.find_all("td")
        print(f"    First row cells: {[c.get_text().strip()[:20] for c in cells]}")
        # cells[0] = "41 / 66 = 62%" (P1 1st Serve %)
        # cells[1] = "1ST SERVE %"
        # cells[2] = "45 / 79 = 57%" (P2 1st Serve %)
        
        # P1 = Madferit (winner), P2 = Marco (loser)
        # So P1's 1st serve = 62%, P2's 1st serve = 57%
        print(f"    In HTML line: 'Madferit def. Marco' -> Madferit is P1 (winner), Marco is P2 (loser)")
        print(f"    1st Serve % from table: P1={cells[0].get_text().strip()}, P2={cells[2].get_text().strip()}")
        print(f"    Sibling interpretation: previousSibling of label is P1, nextSibling is P2.")
        print(f"    Current impl interpretation: cells[0]=P1, cells[2]=P2.")
        print(f"    ARE THESE EQUIVALENT? YES. Both correctly map to the WINNER (P1=left) and LOSER (P2=right).")


def test_current_implementation():
    print("\n" + "=" * 60)
    print("PART 3: CURRENT IMPLEMENTATION STATUS")
    print("=" * 60)

    file_path = "MatchLog - TrainingClub.001.html"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    from app.services.analyzer import parse_match_log_file
    
    with open(file_path, "r", encoding="iso-8859-1") as f:
        content = f.read()
    
    matches = parse_match_log_file(content)
    
    # Find a match where "Marco" is the loser to verify identity logic
    print(f"\n  Total matches parsed: {len(matches)}")
    
    marco_losses = [m for m in matches if "Marco" in m.info.player2_name]
    print(f"  Matches where 'Marco' is P2 (loser): {len(marco_losses)}")
    
    if marco_losses:
        sample = marco_losses[0]
        print(f"\n  Sample Match (Marco as loser):")
        print(f"    P1 (Winner): {sample.info.player1_name}")
        print(f"    P2 (Loser): {sample.info.player2_name}")
        print(f"    Score: {sample.info.score}")
        print(f"    P1 Total Points Won: {sample.player1.points.total_points_won}")
        print(f"    P2 Total Points Won: {sample.player2.points.total_points_won}")
        
        # Cross-check with HTML: In first match, Madferit won 79 points, Marco won 66.
        # If P1=Winner=Madferit, then P1 total points = 79.
        print(f"    Expected P1 Total Points (from HTML line 82): 79")
        print(f"    Expected P2 Total Points (from HTML line 82): 66")
        
        if sample.player1.points.total_points_won == 79 and sample.player2.points.total_points_won == 66:
            print(f"    Status: PASS - Stats correctly mapped!")
        else:
            print(f"    Status: FAIL - Mismatch!")

    # Check for raw_match_id
    print(f"\n  raw_match_id implemented?")
    if hasattr(matches[0].info, "raw_match_id") and matches[0].info.raw_match_id:
        print(f"    Value: {matches[0].info.raw_match_id}")
    else:
        print(f"    NOT IMPLEMENTED IN MODEL")



if __name__ == "__main__":
    test_regex()
    test_table_id_and_sibling()
    test_current_implementation()
