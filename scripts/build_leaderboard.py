import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from dotenv import load_dotenv
from pathlib import Path
from get_event_id import read_current_event

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
REGION = os.getenv("REGION")
TABLE_NAME = os.getenv("TABLE_NAME")
LEADERBOARD_PATH=Path(os.getenv("LEADERBOARD_PATH"))
EVENT_ID = read_current_event()

# --- SETUP ---
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

# --- UTILITIES ---
def ms_to_time(ms):
    mins = int(ms // 60000)
    secs = int((ms % 60000) / 1000)
    ms_remainder = int(ms % 1000)
    return f"{mins}:{secs:02d}.{ms_remainder:03d}"

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


def build_leaderboard(event_id):
    """Aggregate best laps by eventId → driver (independent of car)."""
    items = fetch_items_for_event(event_id)
    leaderboard = {}

    for item in items:
        event = item.get("eventId")
        driver = item.get("driverName")
        lap_time = item.get("lapTime")
        cuts = int(item.get("cuts", 0))
        car = item.get("carModel", "unknown")

        # Skip incomplete or invalid laps
        if not all([event, driver, lap_time]) or cuts > 0:
            continue

        # Convert Decimal/string to float
        if isinstance(lap_time, Decimal):
            lap_time = float(lap_time)
        elif isinstance(lap_time, str):
            lap_time = float(lap_time)

        leaderboard.setdefault(event, {})
        current_best = leaderboard[event].get(driver)

        # Store best lap only
        if current_best is None or lap_time < current_best["lap_ms"]:
            leaderboard[event][driver] = {
                "driver": driver,
                "car": car,
                "lap_ms": lap_time,
                "lap_time": ms_to_time(lap_time)
            }

    # Convert to list of objects sorted by lap time
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
            print("Warning: leaderboard file is corrupt, starting fresh.")
    return {}


def save_leaderboard(leaderboard):
    """Save leaderboard atomically to prevent corruption."""
    temp_path = LEADERBOARD_PATH.with_suffix(".tmp")
    with open(temp_path, "w") as f:
        json.dump(leaderboard, f, indent=2)
    temp_path.replace(LEADERBOARD_PATH)


def update_leaderboard(event_id):
    new_leaderboard = build_leaderboard(event_id)
    existing_leaderboard = load_existing_leaderboard()
    if new_leaderboard == existing_leaderboard:
        print("No change to leaderboard detected")
        pass
    else:
        existing_leaderboard[EVENT_ID] = new_leaderboard.get(EVENT_ID, [])
        save_leaderboard(existing_leaderboard)
        print(f"Leaderboard updated and saved to {LEADERBOARD_PATH}")



# --- MAIN EXECUTION ---
if __name__ == "__main__":
    update_leaderboard(EVENT_ID)
