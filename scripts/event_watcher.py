import os
import json
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import pytz
from get_event_id import get_current_event_id

# --- LOAD ENV ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")

# --- CONFIG ---
CHECK_INTERVAL = 5
SEASON_CONFIG_PATH = Path(os.getenv("SEASON_CONFIG_PATH"))
EVENT_FILE = Path(os.getenv("EVENT_FILE"))
UPDATE_SCRIPT = Path("/home/ubuntu/ac-timeattack-bot/scripts/update_server.py")


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
    print(f"[event_watcher] 📝 Wrote new current event: {event_id}")


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


def trigger_server_update():
    """Run update_server.py to apply new event to AC server."""
    try:
        python_exec = sys.executable  # use the same Python that's running this script
        print(f"[event_watcher] ⚙️  Updating AC server configs using {python_exec}...")
        result = subprocess.run(
            [python_exec, str(UPDATE_SCRIPT)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("[event_watcher] ✅ AC server updated successfully.")
            if result.stdout.strip():
                print(result.stdout.strip())
        else:
            print("[event_watcher] ⚠️ AC server update failed.")
            if result.stderr.strip():
                print(result.stderr.strip())
    except Exception as e:
        print(f"[event_watcher] ❌ Failed to run update script: {e}")


def monitor_current_event():
    """Continuously check seasonConfig.json and update event file if changed."""
    print("[event_watcher] Starting event monitor...")
    last_event = read_current_event()
    last_config_mtime = get_config_mtime()

    while True:
        try:
            # detect season config changes
            mtime = get_config_mtime()
            if mtime != last_config_mtime:
                print("[event_watcher] Detected config file change.")
                last_config_mtime = mtime

            # check if the active event should change
            current_event = get_current_event_id()
            if current_event != last_event:
                print(f"[event_watcher] 🔄 Event changed → {current_event}")
                write_event(current_event)
                trigger_server_update()
                last_event = current_event
            else:
                print(f"[event_watcher] Event unchanged ({current_event})")

        except Exception as e:
            print(f"[event_watcher] Error: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    monitor_current_event()


