import easyocr
import re
import csv
from collections import defaultdict

IMAGE_PATH = "scoreboard_screenshot.png"
CSV_OUTPUT = "parsed_scoreboard.csv"
STAT_HEADERS = ["Goal", "Assist", "Pass", "Interception", "Save", "Score"]

EXPECTED_NAMES = [
    "kurank", "moRise", "Blidibloda", "lil_Hege", "hello9",
    "rengoku", "N2", "ByRio", "BayPatates", "Asselo",
    # Add more as you go!
]
EXPECTED_PLAYER_COUNT = 10  # Set to your league size!

NAME_CORRECTIONS = {
    "hellog": "hello9",
    "Asseld": "Asselo",
    "N2": "N2",
    "9 ByRio": "ByRio",
    # Add more OCR quirks as needed!
}

def fix_name(raw):
    raw = raw.strip()
    if raw in NAME_CORRECTIONS:
        return NAME_CORRECTIONS[raw]
    # Fuzzy fallback: best match if similarity > 0.5
    best = None
    best_ratio = 0.0
    for name in EXPECTED_NAMES:
        r = sum(1 for a, b in zip(raw.lower(), name.lower()) if a == b) / max(len(name), 1)
        if r > best_ratio:
            best_ratio = r
            best = name
    return best if best_ratio > 0.5 else raw

def calc_score(row):
    try:
        G, A, P, I, S = (int(x) for x in row[1:6])
    except Exception:
        return -999999
    return G*1000 + A*500 + P*250 + I*250 + S*500

def group_by_row(easyocr_results, y_tol=18):
    # easyocr_results: list of (box, text, conf)
    row_map = defaultdict(list)
    for res in easyocr_results:
        box, text, conf = res
        y = (box[0][1] + box[2][1]) // 2
        found = False
        for key in row_map:
            if abs(y - key) <= y_tol:
                row_map[key].append((box, text, conf))
                found = True
                break
        if not found:
            row_map[y].append((box, text, conf))
    rows = []
    for key in sorted(row_map.keys()):
        row_items = row_map[key]
        row_items.sort(key=lambda x: x[0][0][0])
        rows.append([text for _, text, _ in row_items])
    return rows

def parse_team_rows_by_column(rows):
    """
    Finds the stat header row, then parses all player rows by column index.
    Returns a list of [name, goal, assist, pass, interception, save, score, is_mvp]
    """
    stat_indexes = {}
    player_rows = []
    header_found = False
    headers_lower = [h.lower() for h in STAT_HEADERS]

    # 1. Find the header row and map stat names to column indexes
    header_row_idx = -1
    for i, row in enumerate(rows):
        cells = [x.strip() for x in row if x.strip()]
        row_lower = [x.lower() for x in cells]
        header_hits = sum(h in row_lower for h in headers_lower)
        if header_hits >= 3:
            for h in STAT_HEADERS:
                if h.lower() in row_lower:
                    stat_indexes[h] = row_lower.index(h.lower())
            score_index = stat_indexes.get("Score", len(cells) - 1)
            header_found = True
            header_row_idx = i
            break

    if not header_found:
        print("[WARN] Stat header row not found!")
        return []

    # 2. Parse all player rows (those after the header)
    for row in rows[header_row_idx+1:]:
        cells = [x.strip() for x in row if x.strip()]
        if not cells or len(cells) < 2:
            continue
        is_mvp = False
        if cells[-1].upper() == "MVP":
            is_mvp = True
            cells = cells[:-1]
        if any("total" in c.lower() for c in cells):
            continue
        # Name is the first non-numeric, non-header cell
        name = None
        for idx, val in enumerate(cells):
            if not val.replace(',', '').isdigit() and val.lower() not in headers_lower:
                name = fix_name(val)
                break
        if not name:
            continue  # No name found
        # Collect stats by mapped index
        stats = []
        for h in STAT_HEADERS:
            si = stat_indexes.get(h)
            stat_val = cells[si] if (si is not None and si < len(cells)) else ""
            stats.append(stat_val.replace(",", ""))
        # Score (ensure it's the rightmost or mapped column)
        score = stats[-1]  # last is always "Score" by mapping
        player_rows.append([name] + stats[:-1] + [score, is_mvp])
    return player_rows

def find_team_sections(rows):
    home_idx = None
    away_idx = None
    for i, row in enumerate(rows):
        line = " ".join(row).lower()
        if "home" in line and home_idx is None:
            home_idx = i
        elif "away" in line and away_idx is None:
            away_idx = i
    if home_idx is None or away_idx is None:
        print("[WARN] HOME or AWAY section not found!")
        return [], []
    home_rows = rows[home_idx+1:away_idx]
    away_rows = rows[away_idx+1:]
    return home_rows, away_rows

def main():
    print("\n--- Referee1.1 ---\n")
    reader = easyocr.Reader(['en'], gpu=False)
    results = reader.readtext(IMAGE_PATH, detail=1, paragraph=False)
    rows = group_by_row(results)

    print("\n[DEBUG] OCR grouped rows (by y):")
    for i, row in enumerate(rows):
        print(f"Row {i}: {row}")

    home_rows, away_rows = find_team_sections(rows)

    parsed = {
        "HOME": parse_team_rows_by_column(home_rows),
        "AWAY": parse_team_rows_by_column(away_rows)
    }

    found_players = []
    valid_players = []
    statful_players = []
    missing_stats_rows = []
    matched_stats = 0
    total_stats = 0

    print("\nTeam | Name | " + " | ".join(STAT_HEADERS) + " | is_mvp")
    print("-" * 85)
    for team in parsed:
        for row in parsed[team]:
            name = row[0]
            is_mvp = row[-1]
            found_players.append(name)
            if name in EXPECTED_NAMES:
                valid_players.append(name)
            stats = row[1:6]
            stats_filled = all(s and s.isdigit() for s in stats)
            if stats_filled:
                statful_players.append(name)
            else:
                missing_stats_rows.append(name)
            if stats_filled and row[-2].isdigit():
                stat_calc = calc_score(row)
                ocr_score = int(row[-2])
                stat_match = stat_calc == ocr_score
                matched_stats += int(stat_match)
                total_stats += 1
                print(f"{team} | " + " | ".join(str(x) for x in row[:-1]) + f" | {is_mvp}" +
                      ("" if stat_match else f"   [!] Score mismatch: calc={stat_calc}"))
            else:
                print(f"{team} | " + " | ".join(str(x) for x in row[:-1]) + f" | {is_mvp}")

    # Output to CSV
    with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Team", "Name"] + STAT_HEADERS + ["is_mvp"])
        for team in parsed:
            for row in parsed[team]:
                output_row = [team] + row[:-1]
                while len(output_row) < (2 + len(STAT_HEADERS)):
                    output_row.insert(len(output_row) - 1, "")
                output_row.append(row[-1])
                writer.writerow(output_row)

    print(f"\n[CSV output written as '{CSV_OUTPUT}']")

    # Accuracy
    player_detection_accuracy = (len(valid_players) / EXPECTED_PLAYER_COUNT) if EXPECTED_PLAYER_COUNT else 0
    stat_detection_accuracy = (len(statful_players) / EXPECTED_PLAYER_COUNT) if EXPECTED_PLAYER_COUNT else 0

    if len(valid_players) == EXPECTED_PLAYER_COUNT:
        print("\nAll expected players found.")
    else:
        print(f"\nMissing players: {', '.join([n for n in EXPECTED_NAMES if n not in valid_players])}")

    print("\n--- Referee1.1 Summary ---")
    print(f"Player Count: {len(valid_players)}/{EXPECTED_PLAYER_COUNT}")
    print(f"Player Detection Accuracy: {player_detection_accuracy*100:.1f}%")
    print(f"Players with All Stats: {len(statful_players)}/{EXPECTED_PLAYER_COUNT} ({stat_detection_accuracy*100:.1f}%)")
    if len(statful_players) < EXPECTED_PLAYER_COUNT:
        print(f"WARNING: Missing stat data for: {', '.join(missing_stats_rows)}")
        print("Try checking your screenshot quality or OCR grouping if this persists.")

if __name__ == "__main__":
    main()
