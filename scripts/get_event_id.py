import os
import json
from dotenv import load_dotenv
from datetime import datetime
import pytz 


load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
SEASON_CONFIG_PATH = os.getenv("SEASON_CONFIG_PATH")

def get_current_event_id():
    """Determine the current event based on CST time and seasonConfig.json."""
    with open(SEASON_CONFIG_PATH, "r") as f:
        config = json.load(f)

    season_num = config.get("season", 1)
    print(season_num)
    now_cst = datetime.now(pytz.timezone("America/Chicago"))

    current_event = None
    current_start = None

    for key, event in config.items():
        if key == "season":
            continue
        try:
            start_date = datetime.strptime(event["startDate"], "%Y-%m-%d")
            start_date_cst = pytz.timezone("America/Chicago").localize(start_date)
        except Exception as e:
            print(f"Skipping {key}: invalid date ({e})")
            continue

        # Choose the latest event that already started
        if start_date_cst <= now_cst and (
            current_start is None or start_date_cst > current_start
        ):
            current_event = key
            current_start = start_date_cst

    if not current_event:
        print("No event has started yet — defaulting to preseason.")
        current_event = "preseason"

    event_id = f"season{season_num}#{current_event}"
    print(f"Current event determined: {event_id}")
    return event_id


if __name__ == "__main__":
    get_current_event_id()
