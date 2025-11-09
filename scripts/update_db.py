import os
import json
import time
from decimal import Decimal
from datetime import datetime
import boto3
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
RESULTS_DIR = os.getenv("RESULTS_DIR")
PROCESSED_FILES_PATH = os.getenv("PROCESSED_FILES_PATH")
REGION = os.getenv("REGION")
print(RESULTS_DIR)
print(REGION)

# --- AWS setup ---
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table("Results")

# --- Load processed file cache ---
if os.path.exists(PROCESSED_FILES_PATH):
    with open(PROCESSED_FILES_PATH) as f:
        processed_files = set(json.load(f))
else:
    processed_files = set()


# --- Helpers ---
def build_event_id(track_name, track_config):
    """Return event ID like 2025-11-magione:default."""
    now = datetime.now()
    year = now.year
    month = f"{now.month:02d}"
    track_config = (track_config or "default").strip()
    return f"{year}-{month}-{track_name}:{track_config}"


def upsert_laps(result):
    """Insert every lap from the 'Laps' array into DynamoDB."""
    track = result.get("TrackName", "unknown")
    track_config = result.get("TrackConfig", "").strip() or "default"
    event_id = build_event_id(track, track_config)

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
            continue  # skip blank entries

        upload_timestamp = datetime.utcnow().isoformat()
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
            "lapTimestamp": lap_timestamp,           # int from AC file
            "uploadTimestamp": upload_timestamp,     # ISO string when processed
        }

        try:
            table.put_item(Item=item)
            print(f"✅ {driver_name} | {car_model} | {track}:{track_config} | {lap.get('LapTime')} ms")
        except Exception as e:
            print(f"❌ DynamoDB insert failed for {driver_name}: {e}")


def process_new_results():
    print("Process new results")
    """Read new JSON files from results folder and upload to DynamoDB."""
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

            # Delete file after successful insert
            os.remove(full_path)
            print(f"🗑️ Deleted {file_name} after success.")
            processed_files.add(file_name)

        except Exception as e:
            print(f"❌ Error processing {file_name}: {e}")

    # Save processed file list
    with open(PROCESSED_FILES_PATH, "w") as f:
        json.dump(list(processed_files), f)

if __name__ == "__main__":
    while True:
        process_new_results()
        time.sleep(60)
