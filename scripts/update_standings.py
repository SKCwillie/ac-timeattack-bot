import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import boto3
from boto3.dynamodb.conditions import Key
from dotenv import load_dotenv
from logs.logger import logger
from bot.post_leaderboard import lookup_real_name, load_registry

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
SEASON_CONFIG_PATH = os.getenv("SEASON_CONFIG_PATH")
SEASON_STANDINGS_PATH = os.getenv("SEASON_STANDINGS_PATH")
STANDINGS_TABLE = os.getenv("STANDINGS_TABLE")
DROP_WEEKS = int(os.getenv("DROP_WEEKS", "2"))

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(STANDINGS_TABLE)


def load_season_events():
    """Return only actual points events (event1, event2, ...)."""
    with open(SEASON_CONFIG_PATH) as f:
        season = json.load(f)

    events = [key for key in season if key.startswith("event")]
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
    Calculate season standings using the Standings DynamoDB table.

    Drop logic:
      - Count how many events exist in seasonConfig (TOTAL_EVENTS)
      - Read DROP_WEEKS from .env
      - Each driver's score = sum of their best (TOTAL_EVENTS - DROP_WEEKS) events
      - Early in the season, if fewer events exist, just use all available.
    """
    logger.info(f"[standings] 🔄 Calculating standings from DynamoDB for {season_key}")

    all_results = get_season_rows(season_key)

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
        # Use screen name (driverName) as the key so it matches your registry
        driver_name = row["driverName"]
        event_id = row["eventId"]
        event_index = int(row.get("eventIndex", 0))
        points = float(row.get("points", 0.0))

        if driver_name not in drivers:
            drivers[driver_name] = []

        drivers[driver_name].append((event_index, event_id, points))

    standings = []

    for driver_name, results in drivers.items():
        # Sort BEST → WORST by points
        sorted_results = sorted(results, key=lambda r: r[2], reverse=True)

        num_available = len(sorted_results)

        # Keep the best (TOTAL_EVENTS - DROP_WEEKS), but not more than we have so far
        num_to_keep = min(COUNTED_EVENTS, num_available)

        kept = sorted_results[:num_to_keep]
        dropped = sorted_results[num_to_keep:]

        total_points = round(sum(r[2] for r in kept), 2)

        standings.append({
            "driver": driver_name,         # screen name; used for registry lookup + display fallback
            "total_points": total_points,
            "kept_events": kept,          # list of (eventIndex, eventId, points)
            "dropped_events": dropped,
            "drops": len(dropped),
            "total_events": num_available
        })

    # Sort final standings DESC by points
    standings.sort(key=lambda x: x["total_points"], reverse=True)

    # Write seasonStandings.json (now list of dicts)
    with open(SEASON_STANDINGS_PATH, "w") as f:
        json.dump(standings, f, indent=2)

    logger.info(f"[standings] 🏆 Updated season standings at {SEASON_STANDINGS_PATH}")

    return standings


def format_for_discord(standings):
    """
    Format standings for Discord.

    Name logic:
      - Look up the driver's screen name in the registry (steam name → real name)
      - If found, display the real name
      - If not found, display the screen name
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
