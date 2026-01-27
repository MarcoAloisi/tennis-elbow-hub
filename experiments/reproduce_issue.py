
import sys
import os
import asyncio
import json

# Add the backend directory to sys.path to allow imports
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.analyzer import parse_match_log_file

def run_reproduction():
    file_path = "MatchLog - TrainingClub.001.html"
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r", encoding="iso-8859-1") as f:
        content = f.read()

    print(f"Parsing {file_path}...")
    try:
        matches = parse_match_log_file(content)
        print(f"Found {len(matches)} matches.")
        
        if matches:
            first_match = matches[0]
            print("\nFirst Match Info:")
            print(f"  P1: {first_match.info.player1_name}")
            print(f"  P2: {first_match.info.player2_name}")
            print(f"  Score: {first_match.info.score}")
            print(f"  Date: {first_match.info.date}")
            print(f"  P1 1st Serve %: {first_match.player1.serve.first_serve_pct}%")
            
            # Check for ID (it shouldn't exist in current model)
            if hasattr(first_match, "raw_match_id"):
                print(f"  Raw Match ID: {first_match.raw_match_id}")
            else:
                print("  Raw Match ID: Not implemented in model")

    except Exception as e:
        print(f"Error parsing file: {e}")

if __name__ == "__main__":
    run_reproduction()
