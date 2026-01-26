import re

def parse_ratio(text):
    text = text.strip()
    if not text:
        return (0, 0, 0.0)

    # Try full format: "X / Y = Z%"
    match = re.match(r"(\d+)\s*/\s*(\d+)\s*=\s*(\d+(?:\.\d+)?)\s*%?", text)
    if match:
        print(f"Matched Full: {text}")
        num = int(match.group(1))
        denom = int(match.group(2))
        pct = float(match.group(3))
        return (num, denom, pct)

    # Try simple ratio: "X / Y"
    match = re.match(r"(\d+)\s*/\s*(\d+)", text)
    if match:
        print(f"Matched Simple: {text}")
        num = int(match.group(1))
        denom = int(match.group(2))
        pct = (num / denom * 100) if denom > 0 else 0.0
        return (num, denom, pct)

    # Try just a number
    match = re.match(r"(\d+)", text)
    if match:
        print(f"Matched Number: {text}")
        return (int(match.group(1)), 0, 0.0)

    return (0, 0, 0.0)

test_cases = [
    "41 / 66 = 62%",
    "41/66=62%",
    "41 / 66",
    "62%",
    "62",
    "41/66 (62%)",
    "0 / 0 = 0%"
]

for t in test_cases:
    print(f"'{t}' -> {parse_ratio(t)}")
