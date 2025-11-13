import sys, os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
sys.path.append(BASE_DIR)
sys.path.append(SCRIPTS_DIR)
import json
import re
import hashlib
import asyncio
import discord
from discord.ext import tasks
from dotenv import load_dotenv
from logs.logger import logger
from get_event_id import read_current_event

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
LEADERBOARD_PATH = os.getenv("LEADERBOARD_PATH")

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

last_hash = None

# --- Helpers ---
def read_leaderboard():
    """Loads entire leaderboard.json (all events)."""
    try:
        with open(LEADERBOARD_PATH) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading leaderboard: {e}")
        return {}

def get_current_event_data():
    """Return (event_id, rows) for just the CURRENT event."""
    event_id = read_current_event()
    all_data = read_leaderboard() or {}
    rows = all_data.get(event_id, [])
    return event_id, rows

def format_event_name(key: str) -> str:
    """Formats eventId like 'season1#preseason2' → 'Season1 - Preseason2'."""
    parts = key.split("#")
    formatted_parts = []
    for part in parts:
        part = re.sub(r"([a-zA-Z])([0-9])", r"\1 \2", part)
        part = part.capitalize()
        formatted_parts.append(part)
    return " - ".join(formatted_parts)

def format_leaderboard(event_id, rows):
    """Creates the Discord message for the current event's leaderboard."""
    event_name = format_event_name(event_id)

    msg = f"**🏁 {event_name} 🏁**\n"
    if not rows:
        msg += "No leaderboard data yet.\n"
        return msg

    for i, entry in enumerate(rows, 1):
        driver = entry.get("driver", "Unknown")
        lap = entry.get("lap_time", "N/A")
        msg += f"{i}. {driver} — {lap}\n"

    return msg

def get_file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None

# --- Watcher Task ---
@tasks.loop(seconds=5)
async def check_leaderboard():
    global last_hash
    try:
        current_hash = get_file_hash(LEADERBOARD_PATH)
        if not current_hash or current_hash == last_hash:
            return

        # Allow partial file write to finish
        await asyncio.sleep(2)
        new_hash = get_file_hash(LEADERBOARD_PATH)
        if new_hash != current_hash:
            return

        last_hash = current_hash

        # Load ONLY current event data
        event_id, rows = get_current_event_data()
        event_name = format_event_name(event_id)
        msg_text = format_leaderboard(event_id, rows)

        channel = bot.get_channel(CHANNEL_ID)

        # Try to edit existing message showing THIS event's leaderboard
        async for message in channel.history(limit=20):
            if message.author == bot.user and event_name in message.content:
                await message.edit(content=msg_text)
                logger.info(f"✏️ Edited leaderboard for {event_name}")
                return

        # If no existing message, post a new one
        await channel.send(msg_text + "\n")
        logger.info(f"🆕 Posted new leaderboard for {event_name}")

    except Exception as e:
        logger.error(f"Error checking leaderboard: {e}")

# --- Bot Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    check_leaderboard.start()

bot.run(DISCORD_TOKEN)

