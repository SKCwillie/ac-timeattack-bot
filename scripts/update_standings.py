import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from dotenv import load_dotenv
from logs.logger import logger

# --- Load .env ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")

SEASON_CONFIG_PATH = os.getenv("SEASON_CONFIG_PATH")
LEADERBOARD_PATH = os.getenv("LEADERBOARD_PATH")
SEASON_STANDINGS_PATH = os.getenv("SEASON_STANDINGS_PATH")

# Scoring system (edit if you want)
POINTS_TABLE = [10, 7, 5, 3, 2]


def load_season_events():
    """Return only actual points events (event1, event2, ...)."""
    with open(SEASON_CONFIG_PATH) as f:
        season = json.load(f)

    events = [key for key in season if key.startswith("event")]
    events.sort()  # ensure event1 → event2 → event3
    return events


def load_leaderboards():
    """Load leaderboard.json from disk."""
    try:
        with open(LEADERBOARD_PATH) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ Could not load leaderboard.json: {e}")
        return {}


def calculate_standings(season_key="season1"):
    # Load existing seasonStandings.json (or create empty structure)
    if os.path.exists(SEASON_STANDINGS_PATH):
        try:
            with open(SEASON_STANDINGS_PATH, "r") as f:
                all_seasons = json.load(f)
        except Exception:
            all_seasons = {}
    else:
        all_seasons = {}

    events = load_season_events()
    lb = load_leaderboards()

    standings = {}

    for event_key in events:
        full_key = f"{season_key}#{event_key}"

        if full_key not in lb:
            continue  # event not done yet

        results = lb[full_key]

        for pos, row in enumerate(results):
            driver = row.get("driver")
            if not driver:
                continue

            points = POINTS_TABLE[pos] if pos < len(POINTS_TABLE) else 0

            if driver not in standings:
                standings[driver] = {
                    "points": 0,
                    "events": 0,
                    "best_pos": 999
                }

            standings[driver]["points"] += points
            standings[driver]["events"] += 1
            standings[driver]["best_pos"] = min(
                standings[driver]["best_pos"],
                pos + 1
            )

    # Sort standings
    final = sorted(
        standings.items(),
        key=lambda x: (-x[1]["points"], x[1]["best_pos"])
    )

    all_seasons[season_key] = final

    with open(SEASON_STANDINGS_PATH, "w") as f:
        json.dump(all_seasons, f, indent=2)

    logger.info(f"🏆 Updated standings for {season_key} at {SEASON_STANDINGS_PATH}")
    return final



def format_for_discord(final):
    msg = "**🏆 Season Standings 🏆**\n\n"
    for i, (driver, data) in enumerate(final, 1):
        msg += f"{i}. {driver} — {data['points']} pts\n"
    return msg


if __name__ == "__main__":
    standings = calculate_standings("season1")
    print(format_for_discord(standings))
