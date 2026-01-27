
import logging
from app.services.analyzer import analyze_match_log

# Setup basic logging
logging.basicConfig(level=logging.INFO)

filepath = r"c:\Users\marco\Desktop\TE4-PROJECT\MatchLog - TrainingClub.001.html"

print(f"Analyzing {filepath}...")
with open(filepath, "r", encoding="iso-8859-1") as f:
    content = f.read()

# Since analyze_match_log expects a single match string usually, 
# but parse_match_log_file splits it.
# Wait, parse_match_log_file is what we need.
from app.services.analyzer import parse_match_log_file

stats = parse_match_log_file(content)

print(f"Parsed {len(stats)} matches.")
total_1st_won = 0
total_1st_total = 0

for i, m in enumerate(stats):
    p1 = m.player1
    # print(f"Match {i}: P1 {p1.name} 1stWon={p1.points.points_on_first_serve_won}")
    total_1st_won += p1.points.points_on_first_serve_won
    total_1st_total += p1.points.points_on_first_serve_total

print("-" * 30)
print(f"Total 1st Won: {total_1st_won}")
print(f"Total 1st Total: {total_1st_total}")
