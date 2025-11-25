import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import pytz
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
from logs.logger import logger


load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
SEASON_CONFIG_PATH = os.getenv("SEASON_CONFIG_PATH")
EVENT_FILE = Path(os.getenv("EVENT_FILE"))
EVENT_TZ = os.getenv("EVENT_TZ", "America/Chicago")
EVENT_START_OFFSET_HOURS=int(os.getenv("EVENT_START_OFFSET_HOURS", 0))

def get_current_event_id():
    """Determine the current event based on CST time and seasonConfig.json."""
    with open(SEASON_CONFIG_PATH, "r") as f:
        config = json.load(f)

    season_num = config.get("season", 1)
    print(season_num)

    tz = pytz.timezone(EVENT_TZ)
    now_cst = datetime.now(tz)

    current_event = None
    current_start = None

    for key, event in config.items():
        if key == "season":
            continue

        try:
            # Parse the date (YYYY-MM-DD)
            start_date = datetime.strptime(event["startDate"], "%Y-%m-%d")

            # Convert to midnight CST
            start_date_cst = tz.localize(start_date)

            # Apply the offset hours
            start_date_cst = start_date_cst + timedelta(hours=EVENT_START_OFFSET_HOURS)

        except Exception as e:
            logger.error(f"Skipping {key}: invalid date ({e})")
            continue

        # Choose the latest event that already started
        if start_date_cst <= now_cst and (
            current_start is None or start_date_cst > current_start
        ):
            current_event = key
            current_start = start_date_cst

    if not current_event:
        logger.info("No event has started yet — defaulting to preseason.")
        current_event = "preseason"

    event_id = f"season{season_num}#{current_event}"
    print(f"Current event determined: {event_id}")
    return event_id


def read_current_event():
    """Read the current event ID from the file updated by event_watcher."""
    if not EVENT_FILE.exists():
        raise FileNotFoundError(
            f"[get_event_id] currentEvent.json not found at {CURRENT_EVENT_PATH}. "
            "Make sure the event_watcher service is running."
        )

    try:
        with open(EVENT_FILE, "r") as f:
            data = json.load(f)
            event_id = data.get("event_id")
            if not event_id:
                raise ValueError("currentEvent.json missing 'event_id' key")
            print(f'Current event from file: {event_id}')
            return event_id
    except json.JSONDecodeError:
        raise ValueError(f"[get_event_id] currentEvent.json is not valid JSON.")




if __name__ == "__main__":
    get_current_event_id()
