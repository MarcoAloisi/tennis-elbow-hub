
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from bs4 import BeautifulSoup
from app.services.analyzer import extract_header_info

from app.services.analyzer import parse_match_log_file

def test_parser_full():
    print("Testing parser with full file...")
    file_path = "MatchLog - TrainingClub.001.html"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r", encoding="iso-8859-1") as f:
        content = f.read()
    
    matches = parse_match_log_file(content)
    print(f"Parsed {len(matches)} matches.")
    
    if len(matches) > 0:
        m = matches[0]
        print(f"\n--- Match 1: {m.info.player1_name} vs {m.info.player2_name} ---")
        print(f"Score: {m.info.score}")
        print(f"Tournament: {m.info.tournament}")
        
        print("\n[Player 1 Stats]")
        print(f"Aces: {m.player1.serve.aces}")
        print(f"Winners: {m.player1.points.winners}")
        print(f"Unforced Errors: {m.player1.points.unforced_errors}")
        print(f"Total Points Won: {m.player1.points.total_points_won}")
        
        print("\n[Player 2 Stats]")
        print(f"Aces: {m.player2.serve.aces}")
        print(f"Winners: {m.player2.points.winners}")
        print(f"Unforced Errors: {m.player2.points.unforced_errors}")
        print(f"Total Points Won: {m.player2.points.total_points_won}")
        
        print(f"\nTotal matches parsed: {len(matches)}")
    else:
        print("No matches parsed!")

if __name__ == "__main__":
    test_parser_full()
