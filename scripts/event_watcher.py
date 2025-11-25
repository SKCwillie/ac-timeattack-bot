import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import discord
import asyncio
import pytz
from get_event_id import get_current_event_id
from update_standings import calculate_standings, format_for_discord
from update_standings_db import update_standings
from logs.logger import logger

# --- LOAD ENV ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")

# --- CONFIG ---
CHECK_INTERVAL = 5
SEASON_CONFIG_PATH = Path(os.getenv("SEASON_CONFIG_PATH"))
EVENT_FILE = Path(os.getenv("EVENT_FILE"))
UPDATE_SCRIPT = Path("/home/ubuntu/ac-timeattack-bot/scripts/update_server.py")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("STANDINGS_CHANNEL_ID"))


async def send_discord_message(msg: str):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        await client.wait_until_ready()
        channel = client.get_channel(DISCORD_CHANNEL_ID)
        if channel is None:
            logger.error("❌ ERROR: Bot cannot see channel:", DISCORD_CHANNEL_ID)
        else:
            await channel.send(msg)
            logger.info("✅ Message sent to Discord")
        await client.close()

    await client.start(DISCORD_TOKEN)


def write_event(event_id):
    """Atomically write current event info to file."""
    tmp_path = EVENT_FILE.with_suffix(".tmp")
    season_key = event_id.split("#")[0]
    logger.info(f"[event_watcher] Season Key: {season_key}")

    data = {
        "event_id": event_id,
        "last_updated": datetime.now(pytz.timezone("America/Chicago")).isoformat()
    }
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    tmp_path.replace(EVENT_FILE)
    logger.info(f"[event_watcher] 📝 Wrote new current event: {event_id}")
    update_standings(season_key)
    logger.info(f"[event_watcher] 🛢 Updated Standings Database: {season_key}")
    standings = calculate_standings(season_key)
    logger.info(f"[event_watcher] 📝 Calculated new standings: {season_key}")
    msg = format_for_discord(standings)
    logger.info("📢 Sending season standings update to Discord...")


    try:
        asyncio.run(send_discord_message(msg))
    except Exception as e:
        logger.error(f"❌ Failed to send standings to Discord: {e}")





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
                logger.info("[event_watcher] Detected config file change.")
                last_config_mtime = mtime

            # check if the active event should change
            current_event = get_current_event_id()
            if current_event != last_event:
                logger.info(f"[event_watcher] 🔄 Event changed → {current_event}")
                write_event(current_event)
                trigger_server_update()
                last_event = current_event
            else:
                print(f"[event_watcher] Event unchanged ({current_event})")

        except Exception as e:
            logger.error(f"[event_watcher] Error: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    monitor_current_event()
