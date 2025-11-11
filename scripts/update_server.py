import os
import json
import subprocess
import configparser
from dotenv import load_dotenv

# --- Load .env ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")

# --- CONFIG ---
ACSERVER_CFG_DIR = "/home/ubuntu/acserver/cfg"
SERVER_CFG_PATH = os.path.join(ACSERVER_CFG_DIR, "server_cfg.ini")
ENTRY_LIST_PATH = os.path.join(ACSERVER_CFG_DIR, "entry_list.ini")

EVENT_FILE = os.getenv("EVENT_FILE")
SEASON_CONFIG_PATH = os.getenv("SEASON_CONFIG_PATH")
SERVICE_NAME = os.getenv("SERVICE_NAME")
TOTAL_SLOTS = int(os.getenv("SERVER_SLOTS"))


def read_current_event():
    """Read currentEvent.json and split into season and event name."""
    try:
        with open(EVENT_FILE) as f:
            data = json.load(f)
            event_id = data.get("event_id")
            if not event_id:
                raise ValueError("Missing 'event_id' key in currentEvent.json")

            parts = event_id.split("#")
            if len(parts) != 2:
                raise ValueError(f"Unexpected event_id format: {event_id}")

            season_key, event_key = parts
            return season_key, event_key

    except FileNotFoundError:
        raise RuntimeError(f"❌ Could not find {EVENT_FILE}")
    except json.JSONDecodeError:
        raise RuntimeError(f"❌ {EVENT_FILE} is not valid JSON")


def load_season_config():
    """Load season_config.json."""
    try:
        with open(SEASON_CONFIG_PATH) as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"❌ Error loading season config: {e}")


def update_server_cfg(event_label: str, track: str, track_config: str, cars: list[str]):
    """Update server_cfg.ini with the new track and car details."""
    config = configparser.ConfigParser(strict=False, delimiters=("="))
    config.optionxform = str  # preserve case
    config.read(SERVER_CFG_PATH)

    # --- Update server info ---
    config["SERVER"]["NAME"] = f"KCR Time Attack - {event_label}"
    config["SERVER"]["TRACK"] = track
    config["SERVER"]["CONFIG_TRACK"] = track_config
    config["SERVER"]["WELCOME_MESSAGE"] = f"Welcome to {event_label}!"
    config["SERVER"]["LOOP_MODE"] = "1"
    config["SERVER"]["REGISTER_TO_LOBBY"] = "0"

    # --- Update allowed cars list ---
    config["SERVER"]["CARS"] = ";".join(cars)

    # --- Optional: if you also want to set the car count ---
    config["SERVER"]["NUM_CARS"] = str(len(cars))

    with open(SERVER_CFG_PATH, "w") as f:
        config.write(f, space_around_delimiters=False)

    print(f"✅ Updated {SERVER_CFG_PATH} with track {track} and cars {cars}")



def update_entry_list(cars: list[str], total_slots: int):
    """Generate entry_list.ini dividing slots evenly across all cars."""
    if not cars:
        raise ValueError("❌ No cars defined for this event")

    num_cars = len(cars)
    slots_per_car = total_slots // num_cars
    remainder = total_slots % num_cars

    entries = []
    car_index = 0
    car_counter = 0

    for i in range(total_slots):
        model = cars[car_index]
        entry = f"""[CAR_{i}]
MODEL={model}
SKIN=default
SPECTATOR_MODE=0
DRIVERNAME=
TEAM=
GUID=
BALLAST=0
RESTRICTOR=0
"""
        entries.append(entry)

        car_counter += 1
        if (car_counter >= slots_per_car and remainder == 0) or (
            remainder > 0 and car_counter >= slots_per_car + 1
        ):
            car_index += 1
            car_counter = 0
            remainder = max(0, remainder - 1)
            if car_index >= num_cars:
                car_index = num_cars - 1  # safeguard

    with open(ENTRY_LIST_PATH, "w") as f:
        f.write("\n".join(entries))

    print(f"✅ Created {ENTRY_LIST_PATH} with {total_slots} slots for {num_cars} cars.")


def restart_acserver():
    """Restart the Assetto Corsa server service."""
    try:
        subprocess.run(["sudo", "systemctl", "restart", SERVICE_NAME], check=True)
        print(f"🔁 Restarted {SERVICE_NAME}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Failed to restart service: {e}")


def main():
    season_key, event_key = read_current_event()
    season = load_season_config()

    if event_key not in season:
        raise RuntimeError(f"❌ Event '{event_key}' not found in season config")

    event = season[event_key]
    track = event.get("track", "")
    track_config = event.get("trackConfig", "")
    cars = event.get("cars", [])

    event_label = f"{season_key}#{event_key}"
    print(f"📅 Applying {event_label}: {track} ({track_config}) with cars {cars}")

    update_server_cfg(event_label, track, track_config, cars)
    update_entry_list(cars, TOTAL_SLOTS)
    restart_acserver()


if __name__ == "__main__":
    main()

