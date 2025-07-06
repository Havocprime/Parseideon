import os
import cv2
import pytesseract
import csv

BASE_Y = 156
ROW_HEIGHT = 46
NUM_ROWS = 10
NUM_COLS = 7
CROP_TOP_PAD = 6
CROP_BOTTOM_PAD = 4

# (x0, x1) for each column, hand-tuned
COL_X = {
    1: (80, 285),      # Name (wider)
    2: (292, 328),     # Goal
    3: (339, 375),     # Assist
    4: (388, 427),     # Pass
    5: (440, 510),     # Interception
    6: (525, 600),     # Save
    7: (1060, 1130),   # Score
}

INPUT_IMAGE = "scoreboard.png"
DEBUG_DIR = "debug_crops"
os.makedirs(DEBUG_DIR, exist_ok=True)

def get_crop_box(row, col):
    y0 = BASE_Y + (row - 1) * ROW_HEIGHT + CROP_TOP_PAD
    y1 = BASE_Y + (row - 1) * ROW_HEIGHT + ROW_HEIGHT - CROP_BOTTOM_PAD
    x0, x1 = COL_X[col]
    return int(x0), int(y0), int(x1), int(y1)

def ocr_image(image, col):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # For stats, up contrast & use adaptive threshold
    if col == 1:
        # Name: allow letters, numbers, _, space
        config = '--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_ '
        _, thresh = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY)
    else:
        # Stat: only digits, stricter threshold, dilate to connect lines
        config = '--psm 7 -c tessedit_char_whitelist=0123456789'
        _, thresh = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
        thresh = cv2.dilate(thresh, kernel, iterations=1)
    return pytesseract.image_to_string(thresh, config=config).strip()

def main():
    print("\n--- Parseidon 2.15: Tuned for Your Screenshot ---\n")
    img = cv2.imread(INPUT_IMAGE)
    if img is None:
        print(f"Error: Couldn't find '{INPUT_IMAGE}'!")
        return

    parsed_rows = []

    for row in range(1, NUM_ROWS + 1):
        parsed_row = []
        print(f"[ROW {row}] ", end="")
        for col in range(1, NUM_COLS + 1):
            x0, y0, x1, y1 = get_crop_box(row, col)
            crop = img[y0:y1, x0:x1]
            debug_path = f"{DEBUG_DIR}/debug_row{row}_col{col}.png"
            cv2.imwrite(debug_path, crop)
            text = ocr_image(crop, col)
            print(f"[Col {col}: '{text}'] ", end="")
            parsed_row.append(text)
        print()
        parsed_rows.append(parsed_row)

    headers = ["Name", "Goal", "Assist", "Pass", "Interception", "Save", "Score"]
    print("\n=== Parsed Scoreboard ===")
    print("{:<16} {:>6} {:>7} {:>7} {:>13} {:>6} {:>7}".format(*headers))
    print("-" * 72)
    for row in parsed_rows:
        print("{:<16} {:>6} {:>7} {:>7} {:>13} {:>6} {:>7}".format(*row))
    print("=" * 72)

    with open("parsed_scoreboard.csv", "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(parsed_rows)
    print("[CSV output written as 'parsed_scoreboard.csv']")

    print("\n[Summary] Rows found:", len(parsed_rows))
    print(f"[Debug crops written to '{DEBUG_DIR}/']\n")

if __name__ == "__main__":
    main()
