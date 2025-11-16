import sys, os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
import json
import time
import hashlib
import discord
from pathlib import Path
from discord.ext import tasks
from dotenv import load_dotenv
from logs.logger import logger

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
STANDINGS_CHANNEL_ID = int(os.getenv("STANDINGS_CHANNEL"))
SEASON_STANDINGS_PATH = os.getenv("SEASON_STANDINGS_PATH")
EVENT_FILE = Path(os.getenv("EVENT_FILE"))
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
last_hash = None


# --- Utility: get MD5 hash to detect when seasonStandings.json changes ---
def file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logger.error(f"[standings] Failed to hash file {path}: {e}")
        return None


# --- Utility: determine current season from currentEvent.json ---
def get_current_season_key() -> str:
    """
    Reads event_id from currentEvent.json and returns "seasonX".
    Example:
        event_id = "season1#event2"
        → "season1"
    """
    try:
        if not EVENT_FILE.exists():
            logger.warning("[standings] EVENT_FILE does not exist")
            return None

        with open(EVENT_FILE, "r") as f:
            data = json.load(f)

        event_id = data.get("event_id")
        if not event_id:
            logger.warning("[standings] event_id missing in EVENT_FILE")
            return None

        # Extract season part → "season1"
        season_key = event_id.split("#")[0]
        return season_key

    except Exception as e:
        logger.error(f"[standings] Failed to read season from EVENT_FILE: {e}")
        return None


# --- Format standings for Discord ----
def format_standings(season_key: str, season_data: list) -> str:
    """
    season_data is the list stored under seasonStandings.json[season_key]
    Format:
        [
           ["driverName", {points, events, best_pos}],
           ...
        ]
    """
    # Extract season number for pretty text
    season_number = season_key.replace("season", "")

    msg = f"**📊 Season {season_number} Standings 📊**\n\n"

    if not season_data:
        return msg + "_No standings yet._"

    for i, (driver, stats) in enumerate(season_data, 1):
        pts = stats.get("points", 0)
        msg += f"{i}. {driver} — {pts} pts\n"

    msg += "\n"
    return msg


# --- Discord bot logic: watch for changes to seasonStandings.json ----
@bot.event
async def on_ready():
    logger.info("[standings] 🟢 bot online")
    watch_standings.start()


@tasks.loop(seconds=5)
async def watch_standings():
    global last_hash

    # Detect file changes
    h = file_hash(SEASON_STANDINGS_PATH)
    if not h or h == last_hash:
        return

    last_hash = h

    # Load multi-season standings
    try:
        with open(SEASON_STANDINGS_PATH, "r") as f:
            all_standings = json.load(f)
    except Exception as e:
        logger.error(f"[standings] Failed to read {SEASON_STANDINGS_PATH}: {e}")
        return

    # Determine which season to display
    season_key = get_current_season_key()
    if not season_key:
        logger.warning("[standings] Cannot determine season; skipping post")
        return

    season_data = all_standings.get(season_key, [])

    # Build Discord message
    msg_text = format_standings(season_key, season_data)

    # Send message
    channel = bot.get_channel(STANDINGS_CHANNEL_ID)
    if not channel:
        logger.error("[standings] Could not access standings channel")
        return

    logger.info(f"[standings] 🆕 Posting standings for {season_key}")
    await channel.send(msg_text)


bot.run(os.getenv("DISCORD_TOKEN"))
