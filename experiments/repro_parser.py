
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
        print("First match info:")
        print(matches[0].info)
        print("Last match info:")
        print(matches[-1].info)
    else:
        print("No matches parsed!")

if __name__ == "__main__":
    test_parser_full()
