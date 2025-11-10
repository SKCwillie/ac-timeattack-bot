import os
import json
import time
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
import boto3
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
RESULTS_DIR = os.getenv("RESULTS_DIR")
PROCESSED_FILES_PATH = os.getenv("PROCESSED_FILES_PATH")
REGION = os.getenv("REGION")
SEASON_CONFIG_PATH = os.getenv("SEASON_CONFIG_PATH")

# --- AWS setup ---
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table("Results")

# --- Load processed file cache ---
if os.path.exists(PROCESSED_FILES_PATH):
    with open(PROCESSED_FILES_PATH) as f:
        processed_files = set(json.load(f))
else:
    processed_files = set()

# --- Load season config ---
with open(SEASON_CONFIG_PATH) as f:
    season_config = json.load(f)


def get_current_event():
    """Return the current event based on Central Time."""
    central = ZoneInfo("America/Chicago")  # CST/CDT zone
    today = datetime.now(central).date()
    active_event_name = None
    active_event_data = None

    for event_name, event_data in season_config.items():
        if event_name == "season":
            continue
        start_date = datetime.strptime(event_data["startDate"], "%Y-%m-%d").date()
        if start_date <= today:
            if not active_event_data or start_date > datetime.strptime(active_event_data["startDate"], "%Y-%m-%d").date():
                active_event_name = event_name
                active_event_data = event_data

    if not active_event_data:
        # Before season start — default to preseason
        active_event_name = "preseason"
        active_event_data = season_config["preseason"]

    season_number = season_config.get("season", 1)
    print(f"📅 Current event (CST): {active_event_name} (season {season_number})")
    return season_number, active_event_name, active_event_data


def build_event_id(season, event_name):
    """Return DynamoDB event ID like season1#event2."""
    return f"season{season}#{event_name}"


def upsert_laps(result):
    """Insert every lap from the 'Laps' array into DynamoDB."""
    season, event_name, event_data = get_current_event()
    event_id = build_event_id(season, event_name)
    track = event_data["track"]
    track_config = event_data.get("trackConfig", "").strip() or "default"
    allowed_cars = event_data.get("cars", [])

    laps = result.get("Laps", [])
    if not laps:
        print(f"⚠️ No laps found for {event_id}")
        return

    for lap in laps:
        driver_name = lap.get("DriverName", "")
        driver_guid = lap.get("DriverGuid", "")
        car_model = lap.get("CarModel", "")

        # Skip laps that don’t match the current event’s cars
        if allowed_cars and car_model not in allowed_cars:
            print(f"🚫 Skipping {driver_name} in {car_model} (not part of current event)")
            continue

        if not driver_guid or not driver_name:
            print("Skipping blank lap")
            continue

        upload_timestamp = datetime.now(ZoneInfo("America/Chicago")).isoformat()
        lap_timestamp = lap.get("Timestamp", 0)

        item = {
            "eventId": event_id,
            "lapKey": f"{driver_guid}#{lap_timestamp}",
            "driverGuid": driver_guid,
            "driverName": driver_name,
            "carModel": car_model,
            "trackName": track,
            "trackConfig": track_config,
            "lapTime": Decimal(str(lap.get("LapTime", 0))),
            "cuts": lap.get("Cuts", 0),
            "ballastKG": lap.get("BallastKG", 0),
            "tyre": lap.get("Tyre", ""),
            "restrictor": lap.get("Restrictor", 0),
            "lapTimestamp": lap_timestamp,
            "uploadTimestamp": upload_timestamp,
            "season": season,
            "eventName": event_name,
        }

        try:
            table.put_item(Item=item)
            print(f"✅ {driver_name} | {car_model} | {event_id} | {lap.get('LapTime')} ms")
        except Exception as e:
            print(f"❌ DynamoDB insert failed for {driver_name}: {e}")


def process_new_results():
    print("Process new results")
    files = [f for f in sorted(os.listdir(RESULTS_DIR)) if f.endswith(".json")]

    for file_name in files:
        full_path = os.path.join(RESULTS_DIR, file_name)
        if file_name in processed_files:
            continue

        print(f"📂 Processing {file_name}...")

        try:
            with open(full_path) as f:
                result = json.load(f)

            upsert_laps(result)
            processed_files.add(file_name)

        except Exception as e:
            print(f"❌ Error processing {file_name}: {e}")

    with open(PROCESSED_FILES_PATH, "w") as f:
        json.dump(list(processed_files), f)


if __name__ == "__main__":
    while True:
        process_new_results()
        time.sleep(60)

