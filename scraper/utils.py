import csv
import re
import os

CSV_COLUMNS = [
    "name", "role", "Batting Style", "Bowling Style", "team",
    "bat_matches", "bat_innings", "bat_runs", "bat_balls", "bat_highest",
    "bat_average", "bat_sr", "bat_not_out", "bat_fours", "bat_sixes",
    "bat_ducks", "bat_50s", "bat_100s", "bat_200s", "bat_300s", "bat_400s",
    "bowl_matches", "bowl_innings", "bowl_balls", "bowl_runs", "bowl_maidens",
    "bowl_wickets", "bowl_avg", "bowl_eco", "bowl_sr", "bowl_bbi",
    "bowl_bbm", "bowl_4w", "bowl_5w", "bowl_10w",
    "player_image_filename",
]

BATTING_LABEL_MAP = {
    "matches": "bat_matches", "mat": "bat_matches", "m": "bat_matches",
    "innings": "bat_innings", "inns": "bat_innings", "inn": "bat_innings",
    "runs": "bat_runs",
    "balls": "bat_balls", "bf": "bat_balls",
    "highest": "bat_highest", "hs": "bat_highest",
    "average": "bat_average", "avg": "bat_average", "ave": "bat_average",
    "sr": "bat_sr",
    "not out": "bat_not_out", "no": "bat_not_out",
    "fours": "bat_fours", "4s": "bat_fours",
    "sixes": "bat_sixes", "6s": "bat_sixes",
    "ducks": "bat_ducks", "0": "bat_ducks",
    "50s": "bat_50s", "50": "bat_50s",
    "100s": "bat_100s", "100": "bat_100s",
    "200s": "bat_200s", "200": "bat_200s",
    "300s": "bat_300s", "300": "bat_300s",
    "400s": "bat_400s", "400": "bat_400s",
}

BOWLING_LABEL_MAP = {
    "matches": "bowl_matches", "mat": "bowl_matches", "m": "bowl_matches",
    "innings": "bowl_innings", "inns": "bowl_innings", "inn": "bowl_innings",
    "balls": "bowl_balls", "b": "bowl_balls",
    "runs": "bowl_runs",
    "maidens": "bowl_maidens", "mdns": "bowl_maidens",
    "wickets": "bowl_wickets", "wkts": "bowl_wickets",
    "avg": "bowl_avg", "ave": "bowl_avg", "average": "bowl_avg",
    "eco": "bowl_eco", "econ": "bowl_eco",
    "sr": "bowl_sr",
    "bbi": "bowl_bbi",
    "bbm": "bowl_bbm",
    "4w": "bowl_4w",
    "5w": "bowl_5w",
    "10w": "bowl_10w",
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def build_image_filename(team: str, player: str) -> str:
    return f"{slugify(team)}__{slugify(player)}.jpg"


def empty_player_row(name: str, team: str) -> dict:
    row = {col: "" for col in CSV_COLUMNS}
    row["name"] = name
    row["team"] = team
    return row


def write_csv(rows: list, path: str) -> None:
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            # ensure all columns present, extras ignored
            writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})
