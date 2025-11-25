import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from dotenv import load_dotenv
from logs.logger import logger
from bot.post_leaderboard import lookup_real_name, load_registry

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
    events = load_season_events()
    lb = load_leaderboards()

    standings = {}

    for event_key in events:
        full_key = f"{season_key}#{event_key}"

        if full_key not in lb:
            continue

        results = lb[full_key]  # already sorted fastest → slowest

        # Winner lap_ms → seconds
        winner_ms = results[0].get("lap_ms")
        if winner_ms is None or winner_ms <= 0:
            continue

        winner_lap = winner_ms / 1000.0

        for pos, row in enumerate(results):
            driver = row.get("driver")
            if not driver:
                continue

            lap_ms = row.get("lap_ms")
            if lap_ms is None or lap_ms <= 0:
                continue

            lap_time = lap_ms / 1000.0

            # --- NEW SCORING FORMULA ---
            points = round(101 * (winner_lap / lap_time), 2)

            if driver not in standings:
                standings[driver] = {
                    "points": 0.0,
                    "events": 0
                }

            standings[driver]["points"] += points
            standings[driver]["events"] += 1

    # Round totals
    for d in standings.values():
        d["points"] = round(d["points"], 2)

    # Sort by points desc
    final = sorted(
        standings.items(),
        key=lambda x: -x[1]["points"]
    )

    with open(SEASON_STANDINGS_PATH, "w") as f:
        json.dump(final, f, indent=2)

    logger.info(f"🏆 Updated season standings at {SEASON_STANDINGS_PATH}")

    return final



def format_for_discord(final):
    registry = load_registry()
    msg = "**🏆 Season Standings 🏆**\n\n"
    for i, (driver, data) in enumerate(final, 1):
        real = lookup_real_name(driver, registry)
        display = real if real else driver
        msg += f"{i}. {display} — {data['points']} pts\n"
    return msg


if __name__ == "__main__":
    standings = calculate_standings("season1")
    print(format_for_discord(standings))
