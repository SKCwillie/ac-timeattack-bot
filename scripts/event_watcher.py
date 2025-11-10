import os
import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import pytz
from get_event_id import get_current_event_id

# --- CONFIG ---
CHECK_INTERVAL = 5
SEASON_CONFIG_PATH = Path(os.getenv("SEASON_CONFIG_PATH"))
EVENT_FILE = Path(os.getenv("EVENT_FILE"))


def write_event(event_id):
    """Atomically write current event info to file."""
    tmp_path = EVENT_FILE.with_suffix(".tmp")
    data = {
        "event_id": event_id,
        "last_updated": datetime.now(pytz.timezone("America/Chicago")).isoformat()
    }
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    tmp_path.replace(EVENT_FILE)


def read_current_event():
    """Return existing event id if file exists."""
    if EVENT_FILE.exists():
        try:
            with open(EVENT_FILE, "r") as f:
                data = json.load(f)
                return data.get("event_id")
        except Exception:
            pass
    return None


def get_config_mtime():
    """Return the last modification time of seasonConfig.json."""
    try:
        return SEASON_CONFIG_PATH.stat().st_mtime
    except FileNotFoundError:
        return 0


def monitor_current_event():
    """Continuously check seasonConfig.json and update event file if changed."""
    print("[event_watcher] Starting event monitor...")
    last_event = read_current_event()
    last_config_mtime = get_config_mtime()

    while True:
        try:
            # Only recompute if config file changed or interval elapsed
            mtime = get_config_mtime()
            if mtime != last_config_mtime:
                print("[event_watcher] Detected config file change.")
                last_config_mtime = mtime

            # Always check the date/time, but this is a fast call
            current_event = get_current_event_id()
            if current_event != last_event:
                print(f"[event_watcher] Event changed → {current_event}")
                write_event(current_event)
                last_event = current_event
            else:
                print(f"[event_watcher] Event unchanged ({current_event})")

        except Exception as e:
            print(f"[event_watcher] Error: {e}")

        # lightweight sleep—low CPU usage
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    monitor_current_event()

