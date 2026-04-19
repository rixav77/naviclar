import re
import random
import asyncio
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

from utils import (
    BATTING_LABEL_MAP, BOWLING_LABEL_MAP,
    build_image_filename, empty_player_row, write_csv,
)

SQUADS_URL = "https://www.cricbuzz.com/cricket-series/9241/indian-premier-league-2026/squads"
BASE_URL = "https://www.cricbuzz.com"
IMAGES_DIR = Path(__file__).parent.parent / "player_images"
CSV_PATH = Path(__file__).parent.parent / "ipl_2026_players.csv"
PARTIAL_CSV_PATH = Path(__file__).parent.parent / "ipl_2026_players_partial.csv"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

TEAMS = [
    "Chennai Super Kings", "Delhi Capitals", "Gujarat Titans",
    "Royal Challengers Bengaluru", "Punjab Kings", "Kolkata Knight Riders",
    "Sunrisers Hyderabad", "Rajasthan Royals", "Lucknow Super Giants",
    "Mumbai Indians",
]


# ---------------------------------------------------------------------------
# Phase 2: Squad listing — get all player profile URLs
# ---------------------------------------------------------------------------

async def get_all_player_urls(page) -> list:
    """Navigate squads page, click each team span, collect all player profile URLs."""
    print(f"\n[INFO] Loading squads page...")
    await page.goto(SQUADS_URL, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    all_players = []
    seen_ids = set()

    for team in TEAMS:
        print(f"[INFO] Loading squad: {team}")

        # Click the team's <span> element in the squad section
        clicked = await page.evaluate(f"""
            () => {{
                const spans = document.querySelectorAll('span');
                for (const s of spans) {{
                    if (s.textContent.trim() === "{team}") {{
                        s.parentElement.click();
                        return true;
                    }}
                }}
                return false;
            }}
        """)

        if not clicked:
            print(f"[WARN] Could not click tab for {team}")

        await asyncio.sleep(random.uniform(1.5, 2.5))

        html = await page.content()
        # Extract profile links: href="/profiles/{id}/{slug}" title="Player Name"
        players = re.findall(r'href="/profiles/(\d+)/([^"]+)"\s+title="([^"]+)"', html)

        new_count = 0
        for pid, slug, name in players:
            if pid not in seen_ids:
                seen_ids.add(pid)
                all_players.append({
                    "team": team,
                    "name": name,
                    "id": pid,
                    "url": f"{BASE_URL}/profiles/{pid}/{slug}",
                })
                new_count += 1

        print(f"  → {new_count} players added (total so far: {len(all_players)})")

    return all_players


# ---------------------------------------------------------------------------
# Phase 3: Player profile parser
# ---------------------------------------------------------------------------

async def scrape_player(page, player_info: dict) -> dict:
    """Scrape one player profile page and return a complete row dict."""
    url = player_info["url"]
    name = player_info["name"]
    team = player_info["team"]

    row = empty_player_row(name, team)

    for attempt in range(3):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(0.5)
            soup = BeautifulSoup(await page.content(), "lxml")

            _parse_personal_info(soup, row)
            _parse_stats_tables(soup, row)
            image_url = _extract_image_url(soup)

            if image_url:
                filename = build_image_filename(team, name)
                await _download_image(page, image_url, filename)
                row["player_image_filename"] = filename

            return row

        except PlaywrightTimeout:
            wait = 2 ** (attempt + 1)
            print(f"[WARN] Timeout for {name} (attempt {attempt+1}/3) — retrying in {wait}s")
            await asyncio.sleep(wait)
        except Exception as e:
            wait = 2 ** (attempt + 1)
            print(f"[WARN] Error scraping {name} (attempt {attempt+1}/3): {e}")
            await asyncio.sleep(wait)

    print(f"[ERROR] Failed to scrape {name} after 3 attempts — recording blanks")
    return row


def _parse_personal_info(soup: BeautifulSoup, row: dict) -> None:
    """Extract Role, Batting Style, Bowling Style from the personal info section."""
    field_map = {
        "role": "role",
        "batting style": "Batting Style",
        "bowling style": "Bowling Style",
    }
    for label_text, csv_col in field_map.items():
        for el in soup.find_all(string=re.compile(rf"^{re.escape(label_text)}$", re.IGNORECASE)):
            parent = el.parent
            value = None
            if parent:
                nxt = parent.find_next_sibling()
                if nxt:
                    value = nxt.get_text(strip=True)
                if not value and parent.parent:
                    nxt2 = parent.parent.find_next_sibling()
                    if nxt2:
                        value = nxt2.get_text(strip=True)
            if value:
                row[csv_col] = value
                break


def _parse_stats_tables(soup: BeautifulSoup, row: dict) -> None:
    """Extract IPL column values from batting and bowling career summary tables."""
    for table in soup.find_all("table"):
        header_row = table.find("tr")
        if not header_row:
            continue
        headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

        # Find the IPL column index dynamically — never hardcode
        ipl_idx = next((i for i, h in enumerate(headers) if h.strip().upper() == "IPL"), None)
        if ipl_idx is None:
            continue

        # Identify batting vs bowling by the nearest preceding heading text
        label_map = None
        for prev in table.find_all_previous():
            text = prev.get_text(strip=True).lower()
            if "batting career" in text:
                label_map = BATTING_LABEL_MAP
                break
            if "bowling career" in text:
                label_map = BOWLING_LABEL_MAP
                break
        if label_map is None:
            continue

        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) <= ipl_idx:
                continue
            label = cells[0].get_text(strip=True).lower().strip()
            value = cells[ipl_idx].get_text(strip=True)
            csv_col = label_map.get(label)
            if csv_col and value and value not in ("-", ""):
                row[csv_col] = value


def _extract_image_url(soup: BeautifulSoup) -> str | None:
    """Find the player photo URL from the profile page."""
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "static.cricbuzz.com" in src and "/img/" in src:
            # Strip query params for cleaner URL
            return src.split("?")[0]
    return None


async def _download_image(page, image_url: str, filename: str) -> None:
    """Download a player image via Playwright's request context."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMAGES_DIR / filename
    if dest.exists():
        return  # Already downloaded
    try:
        response = await page.request.get(image_url)
        if response.ok:
            dest.write_bytes(await response.body())
        else:
            print(f"[WARN] Image {response.status}: {image_url}")
    except Exception as e:
        print(f"[WARN] Image download error for {filename}: {e}")
    await asyncio.sleep(random.uniform(0.5, 1.0))


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

async def main():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        # Phase 2: get all player URLs
        players = await get_all_player_urls(page)
        total = len(players)
        print(f"\n[INFO] Total players found: {total}")

        if total == 0:
            print("[ERROR] No players found — aborting")
            await browser.close()
            return

        # Phase 3–6: scrape each player profile
        for i, player_info in enumerate(players, 1):
            print(f"[INFO] Processing player {i}/{total}: {player_info['name']} ({player_info['team']})")
            row = await scrape_player(page, player_info)
            results.append(row)

            # Intermediate save every 25 players
            if i % 25 == 0:
                write_csv(results, str(PARTIAL_CSV_PATH))
                print(f"[INFO] Checkpoint: {i}/{total} players saved")

            await asyncio.sleep(random.uniform(1.5, 2.5))

        await browser.close()

    # Write final CSV
    write_csv(results, str(CSV_PATH))
    print(f"\n[DONE] {len(results)} players → {CSV_PATH}")
    print(f"[DONE] Images → {IMAGES_DIR}")

    # Cleanup partial file
    if PARTIAL_CSV_PATH.exists():
        PARTIAL_CSV_PATH.unlink()


if __name__ == "__main__":
    asyncio.run(main())
