# IPL 2026 Player Data Scraper

A web scraper that collects all IPL 2026 player data from Cricbuzz, exports a CSV with full batting/bowling stats, downloads player images, and includes a simple player card UI and a ChatGPT classification prompt.

---

## Project Structure

```
naviclar/
├── scraper/
│   ├── scraper.py          # Main scraping script
│   ├── utils.py            # Helper functions
│   └── requirements.txt    # Python dependencies
├── player_images/          # Downloaded player photos
├── ipl_2026_players.csv    # Generated CSV output
├── ui/
│   └── index.html          # Player card UI
└── prompt.txt              # ChatGPT classification prompt
```

---

## Prerequisites

- Python 3.10+
- Google Chrome installed (used by the scraper)

---

## Setup

```bash
# Clone / unzip the project
cd naviclar

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r scraper/requirements.txt

# Install Playwright's Chromium browser
playwright install chromium
```

---

## Running the Scraper

```bash
cd scraper
python scraper.py
```

A Chrome window will open automatically. The scraper will:

1. Load the IPL 2026 squads page on Cricbuzz
2. Click through all 10 team tabs to collect player profile URLs
3. Visit each player's profile page (~248 players)
4. Extract personal info, batting stats, and bowling stats
5. Download the player's photo
6. Save a partial CSV every 25 players (crash protection)
7. Write the final `ipl_2026_players.csv` when complete

**Expected runtime:** 15–20 minutes

---

## Output

### `ipl_2026_players.csv`

One row per player, 36 columns:

| Group | Columns |
|-------|---------|
| Basic info | `name`, `role`, `Batting Style`, `Bowling Style`, `team` |
| Batting stats | `bat_matches` → `bat_400s` (16 columns) |
| Bowling stats | `bowl_matches` → `bowl_10w` (14 columns) |
| Image | `player_image_filename` |

**Stats source:** All batting and bowling figures are from the **IPL column** on each player's Cricbuzz career stats page — not overall career, not T20I. Players with no IPL appearances have blank stat fields.

### `player_images/`

One `.jpg` per player, named:

```
team-name__player-name.jpg
```

Example: `chennai-super-kings__ms-dhoni.jpg`

---

## Viewing the UI

Open `ui/index.html` directly in any browser:

```bash
open ui/index.html
```

The page shows a hardcoded player card for Virat Kohli with his full IPL batting and bowling stats.

---

## ChatGPT Classification Prompt

After running the scraper, you can classify players into performance tiers A / B / C using ChatGPT:

1. Go to [chatgpt.com](https://chatgpt.com)
2. Upload `ipl_2026_players.csv`
3. Paste the contents of `prompt.txt`
4. ChatGPT will return the CSV with a new `player_category` column added

The prompt classifies players **within their own role group** — batters are ranked against other batters, bowlers against other bowlers, and all-rounders against other all-rounders — producing a near-equal A / B / C distribution across the full squad.

---

## Teams Covered

Chennai Super Kings · Delhi Capitals · Gujarat Titans · Royal Challengers Bengaluru · Punjab Kings · Kolkata Knight Riders · Sunrisers Hyderabad · Rajasthan Royals · Lucknow Super Giants · Mumbai Indians
