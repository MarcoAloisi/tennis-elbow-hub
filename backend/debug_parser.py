
import re
from bs4 import BeautifulSoup
import os

# --- MOCKING analyzer.py functions ---

def parse_ratio(text):
    text = text.strip()
    if not text:
        return (0, 0, 0.0)

    # Strategy 1: Ratio
    ratio_match = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if ratio_match:
        num = int(ratio_match.group(1))
        denom = int(ratio_match.group(2))
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if pct_match:
            pct = float(pct_match.group(1))
        else:
            pct = (num / denom * 100) if denom > 0 else 0.0
        return (num, denom, pct)

    # Strategy 2: Percentage
    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if pct_match:
        pct = float(pct_match.group(1))
        return (int(pct), 0, pct)

    # Strategy 3: Number
    match = re.match(r"(\d+)", text)
    if match:
        return (int(match.group(1)), 0, 0.0)

    return (0, 0, 0.0)

def extract_stats_from_table(soup):
    stats = {}
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                p1_val = cells[0].get_text().strip()
                label = cells[1].get_text().strip()
                p2_val = cells[2].get_text().strip()
                if label and label != "&nbsp;":
                    label_upper = label.upper().strip()
                    stats[label_upper] = (p1_val, p2_val)

                if len(cells) >= 7 and cells[3].get_text().strip() in ("", "\xa0"):
                    p1_val2 = cells[4].get_text().strip()
                    label2 = cells[5].get_text().strip()
                    p2_val2 = cells[6].get_text().strip() if len(cells) > 6 else ""
                    if label2 and label2 != "&nbsp;":
                        label_upper2 = label2.upper().strip()
                        stats[label_upper2] = (p1_val2, p2_val2)
    return stats

def analyze_file(filepath):
    print(f"Reading {filepath}...")
    with open(filepath, "r", encoding="iso-8859-1") as f:
        content = f.read()

    chunks = re.split(r"<hr\s*\/?>", content, flags=re.IGNORECASE)
    print(f"Found {len(chunks)} chunks.")

    # Variables to track the bug [69 / 4599]
    total_1st_won_num = 0
    total_1st_won_denom = 0
    
    total_1st_in_num = 0
    total_1st_in_denom = 0
    
    debug_limit = 5

    for i, chunk in enumerate(chunks):
        if not chunk.strip(): continue
        if " def. " not in chunk and " vs " not in chunk: continue

        soup = BeautifulSoup(chunk, "lxml")
        stats = extract_stats_from_table(soup)

        # 1ST SERVE WON %
        label = "1ST SERVE WON %"
        if label in stats:
            p1_raw, p2_raw = stats[label]
            # Try parsing
            p1_res = parse_ratio(p1_raw)
            p2_res = parse_ratio(p2_raw)

            # NOTE: We don't know who the "USER" is, but let's accumulate BOTH to see magnitude
            # Usually user is P1 or P2. 
            # In the user's filtered view, they selected matches.
            # But here let's just print the raw extraction for P1
            
            total_1st_won_num += p1_res[0]
            total_1st_won_denom += p1_res[1]
            
            if i < debug_limit:
                 print(f"Match {i}: Label='{label}' Val='{p1_raw}' -> Parsed={p1_res}")
        else:
             if i < debug_limit: print(f"Match {i}: Label='{label}' NOT FOUND")
             
        # 1ST SERVE % (To compare denominator)
        label_in = "1ST SERVE %"
        if label_in in stats:
             p1_raw, p2_raw = stats[label_in]
             p1_res = parse_ratio(p1_raw)
             total_1st_in_num += p1_res[0]
             total_1st_in_denom += p1_res[1]

    print("-" * 30)
    print(f"TOTAL P1 1st Serve Won Num: {total_1st_won_num}")
    print(f"TOTAL P1 1st Serve Won Denom: {total_1st_won_denom}")
    print(f"TOTAL P1 1st Serve In Num: {total_1st_in_num}")
    print(f"TOTAL P1 1st Serve In Denom: {total_1st_in_denom}")

if __name__ == "__main__":
    analyze_file(r"c:\Users\marco\Desktop\TE4-PROJECT\MatchLog - TrainingClub.001.html")
