import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from dotenv import load_dotenv
from logs.logger import logger
from bot.post_leaderboard import lookup_real_name, load_registry

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
SEASON_CONFIG_PATH = os.getenv("SEASON_CONFIG_PATH")
SEASON_STANDINGS_DIR = os.getenv("SEASON_STANDINGS_DIR")  # directory, not file
STANDINGS_TABLE = os.getenv("STANDINGS_TABLE")
DROP_WEEKS = int(os.getenv("DROP_WEEKS", "2"))

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(STANDINGS_TABLE)

# Ensure standings directory exists
os.makedirs(SEASON_STANDINGS_DIR, exist_ok=True)


def load_season_events():
    """Return only actual points events (event1, event2, ...)."""
    with open(SEASON_CONFIG_PATH) as f:
        season = json.load(f)

    events = [key for key in season.keys() if key.startswith("event")]
    events.sort()  # ensure event1 → event2 → event3
    return events


def get_season_rows(season_key: str):
    """Fetch all rows for this season from DynamoDB Standings table."""
    response = table.query(
        KeyConditionExpression=Key("season").eq(season_key)
    )

    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("season").eq(season_key),
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    return items


def calculate_standings(season_key: str = "season1"):
    """
    Calculate standings using DynamoDB Standings table.
    Drop logic:
      - TOTAL_EVENTS = number of events in seasonConfig
      - COUNTED_EVENTS = TOTAL_EVENTS - DROP_WEEKS
      - Keep best COUNTED_EVENTS per driver (or all if early season)
    """
    logger.info(f"[standings] 🔄 Calculating standings for {season_key}...")

    # Load all season results from DB
    all_results = get_season_rows(season_key)

    # Count total events from season config
    events = load_season_events()
    TOTAL_EVENTS = len(events)
    COUNTED_EVENTS = TOTAL_EVENTS - DROP_WEEKS

    logger.info(
        f"[standings] TOTAL_EVENTS={TOTAL_EVENTS}, DROP_WEEKS={DROP_WEEKS}, "
        f"COUNTED_EVENTS={COUNTED_EVENTS}"
    )

    # driverName → list of (eventIndex, eventId, points)
    drivers = {}

    for row in all_results:
        driver_name = row["driverName"]      # screen name
        event_id = row["eventId"]
        event_index = int(row.get("eventIndex", 0))
        points = float(row.get("points", 0.0))

        if driver_name not in drivers:
            drivers[driver_name] = []

        drivers[driver_name].append((event_index, event_id, points))

    standings = []

    for driver_name, results in drivers.items():
        # Sort best → worst by points
        sorted_results = sorted(results, key=lambda r: r[2], reverse=True)

        num_available = len(sorted_results)
        num_to_keep = min(COUNTED_EVENTS, num_available)

        kept = sorted_results[:num_to_keep]
        dropped = sorted_results[num_to_keep:]

        total_points = round(sum(p for (_, _, p) in kept), 2)

        standings.append({
            "driver": driver_name,
            "total_points": total_points,
            "kept_events": kept,        # list of (eventIndex, eventId, points)
            "dropped_events": dropped,
            "drops": len(dropped),
            "total_events": num_available
        })

    # Sort final standings by points DESC
    standings.sort(key=lambda x: x["total_points"], reverse=True)

    # Save to per-season JSON file
    season_file = os.path.join(SEASON_STANDINGS_DIR, f"{season_key}.json")

    with open(season_file, "w") as f:
        json.dump(
            {
                "season": season_key,
                "last_updated": datetime.now().isoformat(),
                "total_events": TOTAL_EVENTS,
                "drop_weeks": DROP_WEEKS,
                "counted_events": COUNTED_EVENTS,
                "standings": standings
            },
            f,
            indent=2
        )

    logger.info(f"[standings] 🏆 Standings saved → {season_file}")

    return standings


def format_for_discord(standings):
    """
    Format standings for Discord.

    Name logic:
      - Look up the driver's screen name in registry (steam → real name)
      - If found, show real name; else show screen name
    """
    registry = load_registry()
    msg = "**🏆 Season Standings 🏆**\n\n"

    for i, entry in enumerate(standings, 1):
        screen_name = entry["driver"]
        real_name = lookup_real_name(screen_name, registry)
        display_name = real_name if real_name else screen_name

        pts = entry["total_points"]
        msg += f"{i}. {display_name} — {pts} pts\n"

    return msg


if __name__ == "__main__":
    standings = calculate_standings("season1")
    print(format_for_discord(standings))
