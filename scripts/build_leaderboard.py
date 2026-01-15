import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from dotenv import load_dotenv
from pathlib import Path
from get_event_id import read_current_event
from logs.logger import logger

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
REGION = os.getenv("REGION")
TABLE_NAME = os.getenv("TABLE_NAME")
LEADERBOARD_PATH=Path(os.getenv("LEADERBOARD_PATH"))
SEASON_CONFIG_PATH=os.getenv("SEASON_CONFIG_PATH")

# --- SETUP ---
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

# --- UTILITIES ---
def ms_to_time(ms):
    mins = int(ms // 60000)
    secs = int((ms % 60000) / 1000)
    ms_remainder = int(ms % 1000)
    return f"{mins}:{secs:02d}.{ms_remainder:03d}"

def convert_decimals(obj):
    """Recursively convert Decimal to int/float so json.dump works."""
    if isinstance(obj, Decimal):
        # choose int vs float based on whether it has a fractional part
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, list):
        return [convert_decimals(x) for x in obj]
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    return obj


def fetch_items_for_event(event_id):
    """Query DynamoDB for items belonging to a specific eventId (partition key)."""
    items = []
    response = table.query(
        KeyConditionExpression=Key("eventId").eq(event_id)
    )
    items.extend(response.get("Items", []))

    # Handle pagination
    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("eventId").eq(event_id),
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    return items

def load_season_config(path):
    with open(path, "r") as f:
        return json.load(f)

def get_event_config(season_cfg, event_id):
    try:
        _, event_name = event_id.split("#")
    except ValueError:
        logger.error(f"Invalid eventId format: {event_id}")
        return None

    return season_cfg.get(event_name, None)


def build_leaderboard(event_id):
    """Aggregate best laps by eventId → guid (source of truth), independent of car."""

    # Load season configuration and event rules
    season_cfg = load_season_config(SEASON_CONFIG_PATH)
    event_cfg = get_event_config(season_cfg, event_id)

    if not event_cfg:
        logger.error(f"No event config found for {event_id}. Cannot filter leaderboard.")
        return {}

    allowed_track = event_cfg["track"].lower()

    items = fetch_items_for_event(event_id)
    leaderboard = {}

    for item in items:
        event = item.get("eventId")
        driver_name = item.get("driverName")
        guid = item.get("driverGuid") or item.get("guid")  # 🔥 GUID = identity
        lap_time = item.get("lapTime")
        cuts = int(item.get("cuts", 0))
        car = item.get("carModel", "unknown")

        # --- FILTER BY TRACK ONLY ---
        track = item.get("trackName", "").lower()
        if track != allowed_track:
            logger.info(f"[build_leaderboard] Lap track: {track} does not match allowed track: {allowed_track}")
            continue

        # --- Skip invalid laps ---
        if not all([event, guid, lap_time]) or cuts > 0:
            continue

        # Normalize numeric type
        if isinstance(lap_time, Decimal):
            lap_time = float(lap_time)
        elif isinstance(lap_time, str):
            lap_time = float(lap_time)

        leaderboard.setdefault(event, {})
        current_best = leaderboard[event].get(guid)

        # Store best lap per GUID
        if current_best is None or lap_time < current_best["lap_ms"]:
            leaderboard[event][guid] = {
                "guid": guid,
                "driver": driver_name,   # display only, safe to change later
                "car": car,
                "lap_ms": lap_time,
                "lap_time": ms_to_time(lap_time)
            }

    # Format & sort result
    formatted = {}
    for event, drivers in leaderboard.items():
        sorted_entries = sorted(drivers.values(), key=lambda x: x["lap_ms"])
        formatted[event] = sorted_entries

    return formatted


def load_existing_leaderboard():
    """Load the existing leaderboard file if it exists."""
    if LEADERBOARD_PATH.exists():
        try:
            with open(LEADERBOARD_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error("Warning: leaderboard file is corrupt, starting fresh.")
    return {}

def save_leaderboard(leaderboard):
    """Save leaderboard atomically to prevent corruption."""
    temp_path = LEADERBOARD_PATH.with_suffix(".tmp")
    safe = convert_decimals(leaderboard)
    with open(temp_path, "w") as f:
        json.dump(safe, f, indent=2)
    temp_path.replace(LEADERBOARD_PATH)


def update_leaderboard(event_id):
    new_leaderboard = build_leaderboard(event_id)

    current_event_data = new_leaderboard.get(event_id, [])
    if not current_event_data:
        logger.info(f"No valid laps found for {event_id}, skipping write.")
        return

    # Load existing file (may be empty)
    existing = load_existing_leaderboard()

    # If data hasn't changed, skip write
    old_event_data = existing.get(event_id, [])
    if old_event_data == current_event_data:
        logger.info("No change to leaderboard detected.")
        return

    # Append of update only current event
    existing[event_id] = current_event_data

    # Save entire updated file
    save_leaderboard(existing)

    logger.info(f"🔄 Leaderboard updated")


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Look for args starting with --
    manual_event = None
    for arg in sys.argv[1:]:
        if arg.startswith("--"):
            manual_event = arg[2:]  # strip leading --
            break

    if manual_event:
        event_id = manual_event
        logger.info(f"📘 Using manual event override: {event_id}")
    else:
        event_id = read_current_event()
        logger.info(f"📗 Using current event: {event_id}")

    update_leaderboard(event_id)
