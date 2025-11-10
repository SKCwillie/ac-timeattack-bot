import os
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
REGION = os.getenv("REGION")
TABLE_NAME = os.getenv("TABLE_NAME")   # change if needed
EVENT_ID = "season1#preseason"    # change for your active session

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

def build_leaderboard(items):
    """Aggregate best laps by eventId → driver (ignoring car)."""
    leaderboard = {}

    for item in items:
        event = item.get("eventId")
        driver = item.get("driverName")
        lap_time = item.get("lapTime")
        cuts = int(item.get("cuts", 0))

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
        if current_best is None or lap_time < current_best:
            leaderboard[event][driver] = lap_time

    # Sort each event’s leaderboard
    sorted_lb = {}
    for event, drivers in leaderboard.items():
        sorted_lb[event] = sorted(drivers.items(), key=lambda x: x[1])

    return sorted_lb


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print(f"Fetching data for eventId = {EVENT_ID}")
    items = fetch_items_for_event(EVENT_ID)
    print(f"Fetched {len(items)} laps from DynamoDB")

    leaderboard = build_leaderboard(items)
    print(leaderboard)

