import csv
from collections import Counter, defaultdict

# --- Your correction dictionary here ---
correction_dict = {
    "kurank": "kurank",
    "kunirk": "kurank",
    "kurirk": "kurank",
    "kaw": "kurank",
    "moRise": "moRise",
    "Pest": "moRise",
    "raha": "moRise",
    "rach": "moRise",
    "Blidibloda": "Blidibloda",
    "Biriblede": "Blidibloda",
    "Bieiklos": "Blidibloda",
    "Biritles": "Blidibloda",
    "lilHege": "lilHege",
    "li4ege": "lilHege",
    "lace": "lilHege",
    "hellod": "hellod",
    "helod": "hellod",
    "Feo": "hellod",
    "rengoku": "rengoku",
    "es": "rengoku",
    "N2": "N2",
    "NP": "N2",
    "ByRia": "ByRia",
    "AYP": "ByRia",
    "Of": "ByRia",
    "BayParates": "BayParates",
    "BauPaniis": "BayParates",
    "BauPanies": "BayParates",
    "Bolus": "BayParates",
    "Boal": "BayParates",
    "Asselo": "Asselo",
    "Asscla": "Asselo",
    "oa": "Asselo",
    # Add more as needed!
}

# --- Helper Functions ---

def consensus_value(candidates, numeric=False):
    # Remove empty and clearly broken entries
    candidates = [c for c in candidates if c not in ("", None)]
    if not candidates:
        return ""
    if numeric:
        # Keep only numbers
        candidates = [c for c in candidates if str(c).replace('.', '', 1).isdigit()]
    if not candidates:
        return ""
    count = Counter(candidates)
    most_common, freq = count.most_common(1)[0]
    # For numeric, don't allow singletons unless that's all we've got
    if numeric and freq == 1 and len(candidates) > 1:
        # Take median or mean, or just leave blank if crazy
        nums = [int(c) for c in candidates if c.isdigit()]
        if nums:
            nums.sort()
            return str(nums[len(nums)//2])  # median
        else:
            return ""
    return most_common

def fix_name(raw_name):
    # Try correction dictionary, else return as is
    return correction_dict.get(raw_name, raw_name)

def fix_score(candidates):
    # Try to pick a reasonable score (usually 4-digit)
    candidates = [str(c) for c in candidates if c and c != "0"]
    digit_candidates = [c for c in candidates if c.isdigit()]
    likely_scores = [c for c in digit_candidates if len(c) >= 3]
    if likely_scores:
        # Pick the most common
        return consensus_value(likely_scores, numeric=True)
    if digit_candidates:
        return consensus_value(digit_candidates, numeric=True)
    return ""

def parse_row(row):
    """
    Row is: [name_candidates, g_candidates, a_candidates, p_candidates, i_candidates, s_candidates, score_candidates]
    """
    name = consensus_value(row[0])
    name = fix_name(name)
    goals = consensus_value(row[1], numeric=True)
    assists = consensus_value(row[2], numeric=True)
    passes = consensus_value(row[3], numeric=True)
    inter = consensus_value(row[4], numeric=True)
    saves = consensus_value(row[5], numeric=True)
    score = fix_score(row[6])
    # Integrity: if most fields are missing, ignore row
    if sum(bool(x) for x in [name, goals, assists, passes, inter, saves, score]) < 5:
        return None  # Too broken
    return [name, goals, assists, passes, inter, saves, score]

def print_row(row):
    print(f"{row[0]:<15} {row[1]:<5} {row[2]:<7} {row[3]:<7} {row[4]:<13} {row[5]:<7} {row[6]:<7}")

def debug_candidates(row, idx):
    print(f"[ROW {idx+1}]")
    for col_idx, candidates in enumerate(row):
        label = [
            "Name", "Goal", "Assist", "Pass", "Interception", "Save", "Score"
        ][col_idx]
        print(f"  {label}: {candidates}")

def parse_scoreboard(raw_rows):
    clean_rows = []
    for idx, row in enumerate(raw_rows):
        parsed = parse_row(row)
        if parsed:
            clean_rows.append(parsed)
    return clean_rows

# --- MAIN SCRIPT STARTS HERE ---
print("\n--- Parseidon 3.5: Consensus & Clean Output Edition ---\n")

# Simulate your detected raw_rows (in production, your OCR process fills this)
# Each "row" is a list of lists: one list per cell of candidate values
raw_rows = [
    # Example row: [name_candidates, goal_candidates, assist_candidates, pass_candidates, int_candidates, save_candidates, score_candidates]
    [["kurank", "kurank", "kunirk", "kurirk", "kaw", "kaw"], ["4", "4", "2", "2"], ["0", "0", "0", "0", "0", "0"], ["5", "5", "5", "5"], ["4", "4", "4", "4", "4", "4"], [], ["3840", "3840", "0"]],
    [["moRise", "moRise", "Pest", "Pest", "raha", "rach"], [], ["0", "0", "0", "0", "0", "0"], ["5", "5", "5", "5"], ["3", "3", "2", "2", "3", "3"], ["5", "3"], ["2780", "2780", "2780", "2780", "2780", "2780"]],
    [["Blidibloda", "Blidibloda", "Biriblede", "Biriblede", "Bieiklos", "Biritles"], [], ["0", "0", "0", "0", "0", "0"], ["3", "3", "2", "2"], ["2", "2", "2", "2", "2", "2", "2", "2"], ["0"], ["2670", "2670", "20", "2840", "0", "2670", "7"]],
    [["lilHege", "lilHege", "li4ege", "li4ege", "lace", "lace"], [], ["0", "0", "0", "0"], ["3", "3", "2", "2"], ["2", "2", "2", "2", "2", "2", "2"], ["3", "3", "3", "3", "3", "4"], ["270", "270", "221", "321", "4", "4"]],
    [["hellod", "hellod", "helod", "helod", "Feo", "Feo"], [], ["0", "0", "0"], ["2", "2", "2", "2", "2", "2"], ["3", "3", "3", "3", "2", "2", "4", "4"], ["2", "2"], ["1850", "1850", "50", "50", "15", "0"]],
    [["rengoku", "rengoku", "es", "es"], ["9", "9"], ["3", "3", "0", "0"], ["7", "7", "7", "7", "7"], ["5", "5", "5", "5", "5"], ["13", "13"], ["06800", "0600", "600"]],
    [["N2", "N2", "NP", "NP"], ["1", "1", "1", "1", "1", "1", "1", "1"], ["0", "0", "0", "0"], ["2", "2", "2"], ["1", "1", "1", "1", "1", "1", "1", "1"], ["0", "0"], ["2310", "2310"]],
    [["ByRia", "ByRia", "AYP", "AYP", "Of", "Of"], [], ["0", "0", "0", "0", "0", "0"], ["2", "2", "2", "2"], ["4", "4", "4", "4", "4", "4"], ["0"], ["2060", "2060", "2069", "2089"]],
    [["BayParates", "BayParates", "BauPaniis", "BauPanies", "Bolus", "Boal"], ["1", "1"], ["0", "0", "0", "0"], ["1", "1", "1", "1", "1", "1", "1", "1"], ["2", "2", "2", "2", "2", "2"], [], ["1310", "1310", "110", "110", "1", "1", "10"]],
    [["Asselo", "Asselo", "Asscla", "Asscla", "oa", "oa"], [], ["0", "0", "0", "0", "0", "0"], ["1", "1", "1", "1", "1", "1", "1", "1"], ["0", "0"], [], ["750", "750", "750", "73"]],
]

# Debug print all candidate values
print("=== Debug Candidates ===")
for idx, row in enumerate(raw_rows):
    debug_candidates(row, idx)
print("")

# Parse all rows
clean_rows = parse_scoreboard(raw_rows)

# Print the cleaned scoreboard
print("=== Parsed Scoreboard ===")
print(f"{'Name':<15} {'Goal':<5} {'Assist':<7} {'Pass':<7} {'Interception':<13} {'Save':<7} {'Score':<7}")
print("-" * 72)
for row in clean_rows:
    print_row(row)
print("=" * 72)

# Write CSV
csv_filename = "parsed_scoreboard.csv"
with open(csv_filename, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Name", "Goal", "Assist", "Pass", "Interception", "Save", "Score"])
    for row in clean_rows:
        writer.writerow(row)
print(f"[CSV output written as '{csv_filename}']")

print("\n[Summary] Rows found:", len(clean_rows))
print("[Debug candidates printed above for reference]")

# Optionally, write debug CSV with all candidates (for your own dev work)
with open("debug_candidates.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Name_candidates", "Goal_candidates", "Assist_candidates", "Pass_candidates", "Interception_candidates", "Save_candidates", "Score_candidates"])
    for row in raw_rows:
        writer.writerow(row)
print("[Debug candidate output written as 'debug_candidates.csv']")
