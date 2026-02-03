import sys
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.analyzer import extract_header_info, MatchInfo

# Sample HTML snippets
samples = [
    # Strict format with ELOs
    """<p>Roger Federer (ELO: 2500) def. Rafael Nadal (ELO: 2450) : 6-4 6-4 - Wimbledon - 1:30'00 (1:45'00) - 2023-07-15 [Online]</p>""",
    # Fallback with ELOs in names (Regex split style)
    """<p>Novak Djokovic (ELO: 2600) def. Andy Murray (ELO: 2100) : 6-3 6-3 - Australian Open - 1:20'00 - 2023-01-20</p>""",
    # No ELOs
    """<p>Carlos Alcaraz def. Jannik Sinner : 7-6 7-6 - US Open - 2:00'00 - 2023-09-10</p>""",
    # One ELO (Mixed)
    """<p>Daniil Medvedev (ELO: 2300) def. Nick Kyrgios : 6-2 6-2 - Miami Open - 1:00'00 - 2023-03-20</p>"""
]

print("Verifying ELO Extraction...")
for i, html in enumerate(samples):
    print(f"\n--- Sample {i+1} ---")
    print(f"Input: {html.strip()}")
    try:
        soup = BeautifulSoup(html, 'html.parser') # Use html.parser in case lxml is missing in this env
        info = extract_header_info(soup)
        if info:
            print(f"  P1: '{info.player1_name}' | ELO: {info.player1_elo}")
            print(f"  P2: '{info.player2_name}' | ELO: {info.player2_elo}")
            print(f"  Score: {info.score}")
        else:
            print("  FAILED: Could not extract info")
    except Exception as e:
        print(f"  ERROR: {e}")
