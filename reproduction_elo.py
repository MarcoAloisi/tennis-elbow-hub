import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.analyzer import analyze_match_log

# Mock HTML with ELO
html_content = """
<html>
<body>
<p>Player1 (ELO: 2000 +10) def. Player2 (ELO: 1900 -10) : 6/0 6/0 - Tournament - 0:30'00 (0:30'00) - 2026-02-06</p>
<table>
<tr><td>10/20</td><td>1st Serve %</td><td>10/20</td><td></td><td></td><td></td><td></td></tr>
<tr><td>1</td><td>Aces</td><td>1</td><td></td><td></td><td></td><td></td></tr>
<tr><td>1</td><td>Double Faults</td><td>1</td><td></td><td></td><td></td><td></td></tr>
<tr><td>200 km/h</td><td>Fastest Serve</td><td>200 km/h</td><td></td><td>AVERAGE RALLY LENGTH: 4.0</td><td></td><td></td></tr>
<tr><td>180 km/h</td><td>Avg 1st Serve</td><td>180 km/h</td><td></td><td>0</td><td></td><td></td></tr>
<tr><td>150 km/h</td><td>Avg 2nd Serve</td><td>150 km/h</td><td></td><td>0</td><td></td><td></td></tr>
<tr><td>10</td><td>Winners</td><td>10</td><td></td><td>50%</td><td></td><td></td></tr>
<tr><td>5</td><td>Forced Errors</td><td>5</td><td></td><td>50%</td><td></td><td></td></tr>
<tr><td>5</td><td>Unforced Errors</td><td>5</td><td></td><td>10/20</td><td></td><td></td></tr>
<tr><td>2/2</td><td>Net Points Won</td><td>2/2</td><td></td><td>1</td><td></td><td></td></tr>
<tr><td>1/1</td><td>Break Points Won</td><td>1/1</td><td></td><td>1/1</td><td></td><td></td></tr>
<tr><td>50</td><td>Total Points Won</td><td>30</td><td></td><td></td><td></td><td></td></tr>
</table>
</body>
</html>
"""

stats = analyze_match_log(html_content)

if stats:
    print(f"Player 1: {stats.player1.name}")
    print(f"P1 ELO: {stats.player1.general.elo}")
    print(f"P1 ELO Diff: {stats.player1.general.elo_diff}")
    
    print(f"Player 2: {stats.player2.name}")
    print(f"P2 ELO: {stats.player2.general.elo}")
    print(f"P2 ELO Diff: {stats.player2.general.elo_diff}")

    if stats.player1.general.elo == 2000 and stats.player1.general.elo_diff == 10:
        print("SUCCESS: Player 1 ELO parsed correctly.")
    else:
        print("FAILURE: Player 1 ELO incorrect.")
        
    if stats.player2.general.elo == 1900 and stats.player2.general.elo_diff == -10:
        print("SUCCESS: Player 2 ELO parsed correctly.")
    else:
        print("FAILURE: Player 2 ELO incorrect.")

else:
    print("FAILURE: Stats extraction failed.")
