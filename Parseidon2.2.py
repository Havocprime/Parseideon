import easyocr
from PIL import Image
import numpy as np
import csv
from collections import defaultdict

# === CONFIG ===
IMAGE_PATH = "screenshot2.png"
CSV_OUTPUT = "parsed_scoreboard.csv"
EXPECTED_NAMES = [
    "Kolanis", "jfk_bruh", "MoistTowelette",  # HOME
    "Snax", "Froggy", "w33b"                  # AWAY
]
EXPECTED_PLAYER_COUNT = 6
STAT_HEADERS = ["Name", "Goal", "Assist", "Pass", "Interception", "Save", "Score", "is_mvp"]

# Estimated cropping coordinates (for your screenshot)
ROW_COORDS = [
    (237, 281),  # Home 1
    (281, 325),  # Home 2
    (325, 369),  # Home 3
    (403, 447),  # Away 1
    (447, 491),  # Away 2
    (491, 535),  # Away 3
]
X_START = 340
X_END = 1170

NAME_CORRECTIONS = {
    "jfk bruh": "jfk_bruh",
    "Moist Towelette": "MoistTowelette",
    "Snax": "Snax",
    "Froggy": "Froggy",
    "w33b": "w33b"
}

# === Full-table OCR Logic ===
def group_by_row(easyocr_results, y_tol=28):
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

def find_stat_header_row(rows):
    headers_lower = [h.lower() for h in STAT_HEADERS[1:-2] + ["Score"]]  # skip "Name", include "Score"
    best_idx = -1
    best_count = 0
    best_map = {}
    for idx, row in enumerate(rows):
        row_lower = [x.lower() for x in row]
        stat_map = {}
        count = 0
        for h in headers_lower:
            if h in row_lower:
                stat_map[h] = row_lower.index(h)
                count += 1
        if count > best_count:
            best_count = count
            best_map = stat_map
            best_idx = idx
    if best_count >= 3:
        return best_idx, best_map
    else:
        return -1, {}

def fix_name(raw):
    raw = raw.strip()
    # Use corrections
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

def parse_team_rows_smart(rows):
    header_row_idx, stat_indexes = find_stat_header_row(rows)
    player_rows = []
    headers_lower = [h.lower() for h in STAT_HEADERS]
    if header_row_idx == -1 or not stat_indexes:
        print("[WARN] Stat header row not found (Full-table). Will parse by [name, score] only.")
        header_row_idx = 0
    for row in rows[header_row_idx+1:]:
        cells = [x.strip() for x in row if x.strip()]
        if not cells or len(cells) < 2:
            continue
        if any(s in cells[0].lower() for s in ["total", "match", "victory", "progression", "ranking", "back"]):
            continue
        is_mvp = False
        if cells and cells[-1].upper() == "MVP":
            is_mvp = True
            cells = cells[:-1]
        name = fix_name(cells[0])
        stats = []
        # Fill with stats if present, otherwise pad
        for i in range(1, len(STAT_HEADERS) - 2):  # -2: skip "Name" and "is_mvp"
            if i < len(cells):
                stats.append(cells[i])
            else:
                stats.append("0")  # or "" for blank
        # Score (always try to take last value)
        score = cells[-1] if len(cells) > 1 else "0"
        player_row = [name] + stats + [score, is_mvp]
        print(f"[DEBUG] Parsed player row: {player_row} (raw cells: {cells})")
        player_rows.append(player_row)
    return player_rows


# === Row-cropping OCR Logic ===
def crop_rows(image_path, row_coords, x_start, x_end):
    img = Image.open(image_path)
    cropped_rows = []
    for i, (y_start, y_end) in enumerate(row_coords):
        crop_box = (x_start, y_start, x_end, y_end)
        row_img = img.crop(crop_box)
        cropped_rows.append(row_img)
    return cropped_rows

def ocr_rows(row_images):
    reader = easyocr.Reader(['en'], gpu=False)
    results = []
    for idx, row_img in enumerate(row_images):
        ocr_result = reader.readtext(np.array(row_img), detail=0, paragraph=True)
        if ocr_result:
            results.append(ocr_result[0])
        else:
            results.append("")
    return results

def parse_row_text(row_text):
    values = row_text.replace(",", "").split()
    is_mvp = False
    if values and values[-1].upper() == "MVP":
        is_mvp = True
        values = values[:-1]
    while len(values) < len(STAT_HEADERS) - 1:
        values.append("")
    values = values[:len(STAT_HEADERS) - 1]
    return values + [is_mvp]

# === Output and Control ===
def print_rows_debug(rows, title):
    print(f"\n[DEBUG] {title}:")
    for i, row in enumerate(rows):
        print(f"Row {i}: {row}")

def output_csv(rows, csv_output):
    with open(csv_output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(STAT_HEADERS)
        for row in rows:
            writer.writerow(row)
    print(f"\n[CSV output written as '{csv_output}']")

def main():
    print("\n--- Parseidon 2.2: Hybrid Table & Row OCR ---\n")
    # Step 1: Full-table OCR
    reader = easyocr.Reader(['en'], gpu=False)
    results = reader.readtext(IMAGE_PATH, detail=1, paragraph=False)
    print("\n[DEBUG] RAW OCR OUTPUT:")
    for i, (box, text, conf) in enumerate(results):
        print(f"{i}: '{text}' @ {box} (conf={conf:.2f})")
    rows = group_by_row(results, y_tol=28)
    print_rows_debug(rows, "Full-table OCR grouped rows (y_tol=28)")
    team_rows = rows
    fulltable_rows = parse_team_rows_smart(team_rows)

    # Diagnostics
    num_stats = sum(1 for row in fulltable_rows for v in row[1:-2] if v.isdigit())
    enough_stats = num_stats >= EXPECTED_PLAYER_COUNT  # At least one stat per player
    if fulltable_rows and enough_stats:
        print(f"\n[Full-table OCR] Parsed {len(fulltable_rows)} player rows with stats.")
        for row in fulltable_rows:
            print(row)
        output_csv(fulltable_rows, CSV_OUTPUT)
        print(f"[Summary] Approach: Full-table OCR. Rows found: {len(fulltable_rows)}")
        return
    else:
        print(f"\n[Full-table OCR] Incomplete stats detected. Falling back to Row Crop OCR...")

    # Step 2: Row-cropping OCR (fallback)
    row_images = crop_rows(IMAGE_PATH, ROW_COORDS, X_START, X_END)
    print(f"Cropped {len(row_images)} player rows.")
    ocr_results = ocr_rows(row_images)
    parsed_rows = [parse_row_text(t) for t in ocr_results]
    print("\nParsed rows (Row Crop OCR):")
    for row in parsed_rows:
        print(row)
    output_csv(parsed_rows, CSV_OUTPUT)
    print(f"[Summary] Approach: Row-crop OCR. Rows found and cropped: {len(parsed_rows)}")

if __name__ == "__main__":
    main()
