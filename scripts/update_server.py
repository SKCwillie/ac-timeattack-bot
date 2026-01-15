import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import time
import subprocess
import configparser
from itertools import cycle
from dotenv import load_dotenv
from logs.logger import logger

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

def get_skins_for_car(car_folder: str):
    skins_path = f"/home/ubuntu/acserver/content/cars/{car_folder}/skins"

    if not os.path.exists(skins_path):
        return []

    skins = [
        name for name in os.listdir(skins_path)
        if os.path.isdir(os.path.join(skins_path, name))
           and not name.startswith(".")
    ]

    skins.sort()
    return skins

def assign_skins(car_folder: str, num_slots: int):
    skins = get_skins_for_car(car_folder)

    if not skins:
        return ["default"] * num_slots

    cyc = cycle(skins)
    return [next(cyc) for _ in range(num_slots)]


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

    logger.info(f"✅ Updated {SERVER_CFG_PATH} with track {track} and cars {cars}")



def update_entry_list(cars: list[str], total_slots: int):
    """Generate entry_list.ini assigning skins per car and cycling when needed."""
    if not cars:
        raise ValueError("❌ No cars defined for this event")

    num_cars = len(cars)
    slots_per_car = total_slots // num_cars
    remainder = total_slots % num_cars

    entries = []
    car_index = 0
    car_counter = 0

    # Pre-compute how many slots each car gets
    car_slot_counts = []
    for i in range(num_cars):
        extra = 1 if i < remainder else 0
        car_slot_counts.append(slots_per_car + extra)

    # Assign skins for each car (in advance)
    car_skins = {}
    for car, count in zip(cars, car_slot_counts):
        car_skins[car] = assign_skins(car, count)

    slot_num = 0
    for car_idx, car in enumerate(cars):
        skins_for_car = car_skins[car]

        for skin in skins_for_car:
            entry = f"""[CAR_{slot_num}]
MODEL={car}
SKIN={skin}
SPECTATOR_MODE=0
DRIVERNAME=
TEAM=
GUID=
BALLAST=0
RESTRICTOR=0
"""
            entries.append(entry)
            slot_num += 1

    with open(ENTRY_LIST_PATH, "w") as f:
        f.write("\n".join(entries))

    logger.info(
        f"✅ Created {ENTRY_LIST_PATH} with {total_slots} slots for {num_cars} cars (skins assigned)."
    )


def restart_acserver():
    """Restart the Assetto Corsa server service."""
    try:
        subprocess.run(["sudo", "systemctl", "restart", SERVICE_NAME], check=True)
        logger.info(f"🔁 Restarted {SERVICE_NAME}")
    except subprocess.CalledProcessError as e:
        logger.info(f"⚠️ Failed to restart service: {e}")


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
    logger.info(f"📅 Applying {event_label}: {track} ({track_config}) with cars {cars}")

    update_server_cfg(event_label, track, track_config, cars)
    update_entry_list(cars, TOTAL_SLOTS)
    restart_acserver()


if __name__ == "__main__":
    main()

