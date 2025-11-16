import os
import json
import hashlib
from pathlib import Path
import discord
from discord.ext import tasks
from dotenv import load_dotenv
from logs.logger import logger
from bot.utils import load_registry, lookup_real_name

# --- ENV ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
STANDINGS_CHANNEL_ID = int(os.getenv("STANDINGS_CHANNEL_ID"))
SEASON_STANDINGS_PATH = os.getenv("SEASON_STANDINGS_PATH")  # multi-season json
EVENT_FILE = Path(os.getenv("EVENT_FILE"))                  # currentEvent.json
REGISTRY_PATH = Path(os.getenv("REGISTRY_PATH"))
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
last_hash = None

# Utility: get MD5 to detect file changes

def file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logger.error(f"[standings] Failed to hash {path}: {e}")
        return None


# Determine current season from currentEvent.json
def get_current_season_key():
    try:
        if not EVENT_FILE.exists():
            logger.warning("[standings] EVENT_FILE not found")
            return None

        with open(EVENT_FILE, "r") as f:
            data = json.load(f)

        event_id = data.get("event_id")
        if not event_id:
            return None

        # "season1#event3" → "season1"
        return event_id.split("#")[0]

    except Exception as e:
        logger.error(f"[standings] Failed reading EVENT_FILE: {e}")
        return None


# Format standings for Discord
def format_standings(season_key: str, season_data: list):
    """
    season_data is array under:
      {
         "season1": [ ["driver", {...}], ... ]
      }
    """

    registry = load_registry(REGISTRY_PATH)

    # "season1" → "1"
    season_number = season_key.replace("season", "")

    msg = f"**📊 Season {season_number} Standings 📊**\n\n"

    if not season_data:
        return msg + "_No standings yet._"

    for i, (steam_name, stats) in enumerate(season_data, 1):
        real_name = lookup_real_name(steam_name, registry)
        display = real_name if real_name else steam_name

        pts = stats.get("points", 0)
        msg += f"{i}. {display} — {pts} pts\n"

    return msg + "\n"


# Discord Bot: Poll for changes to seasonStandings.json
@bot.event
async def on_ready():
    logger.info("[standings] 🟢 post_standings bot online")
    watch_standings.start()


@tasks.loop(seconds=5)
async def watch_standings():
    global last_hash

    # Detect file changes
    h = file_hash(SEASON_STANDINGS_PATH)
    if not h or h == last_hash:
        return
    last_hash = h

    # Load multi-season file
    try:
        with open(SEASON_STANDINGS_PATH, "r") as f:
            all_standings = json.load(f)
    except Exception as e:
        logger.error(f"[standings] Unable to read file: {e}")
        return

    # Determine which season to post
    season_key = get_current_season_key()
    if not season_key:
        logger.warning("[standings] No valid season key found")
        return

    season_data = all_standings.get(season_key, [])

    # Build Discord message
    msg_text = format_standings(season_key, season_data)

    # Send message
    channel = bot.get_channel(STANDINGS_CHANNEL_ID)
    if not channel:
        logger.error("[standings] Could not access standings channel")
        return

    logger.info(f"[standings] 🆕 Posting new standings for {season_key}")
    await channel.send(msg_text)


bot.run(os.getenv("DISCORD_TOKEN"))
