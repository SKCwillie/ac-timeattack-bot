import os
import json
import time
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
import boto3
from dotenv import load_dotenv
from get_event_id import read_current_event
from build_leaderboard import update_leaderboard

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
RESULTS_DIR = os.getenv("RESULTS_DIR")
PROCESSED_FILES_PATH = os.getenv("PROCESSED_FILES_PATH")
REGION = os.getenv("REGION")

# --- AWS setup ---
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table("Results")

# --- Load processed file cache ---
if os.path.exists(PROCESSED_FILES_PATH):
    with open(PROCESSED_FILES_PATH) as f:
        processed_files = set(json.load(f))
else:
    processed_files = set()


def upsert_laps(result):
    """Insert every lap from the 'Laps' array into DynamoDB for the current event."""
    # ✅ Get current eventId directly from file maintained by event_watcher
    event_id = read_current_event()
    track = result.get("TrackName", "unknown")
    track_config = result.get("TrackConfig", "").strip() or "default"
    laps = result.get("Laps", [])

    if not laps:
        print(f"⚠️ No laps found for {event_id}")
        return

    for lap in laps:
        driver_name = lap.get("DriverName", "")
        driver_guid = lap.get("DriverGuid", "")
        car_model = lap.get("CarModel", "")

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
            "uploadTimestamp": upload_timestamp
        }

        try:
            table.put_item(Item=item)
            print(f"✅ {driver_name} | {car_model} | {event_id} | {lap.get('LapTime')} ms")
        except Exception as e:
            print(f"❌ DynamoDB insert failed for {driver_name}: {e}")


def process_new_results():
    """Scan results folder and process any unprocessed result files."""
    print("Process new results")
    files = [f for f in sorted(os.listdir(RESULTS_DIR)) if f.endswith(".json")]
    new_data = False

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
            new_data = True

        except Exception as e:
            print(f"❌ Error processing {file_name}: {e}")

    with open(PROCESSED_FILES_PATH, "w") as f:
        json.dump(list(processed_files), f)

    if new_data:
        try:
            event_id = read_current_event()
            update_leaderboard(event_id)
            print("🏁 Leaderboard successfully updated.")
        except Exception as e:
            print(f"❌ Failed to update leaderboard: {e}")



if __name__ == "__main__":
    while True:
        process_new_results()
        time.sleep(10)

