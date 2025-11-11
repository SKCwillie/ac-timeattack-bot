import os
import time
import json
import re
import hashlib
import asyncio
import discord
from discord.ext import tasks
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
LEADERBOARD_PATH = os.getenv("LEADERBOARD_PATH")
LEADERBOARD_MSG_ID_PATH = os.getenv("LEADERBOARD_MSG_ID_PATH")

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

last_hash = None

# --- Helpers ---
def read_leaderboard():
    try:
        with open(LEADERBOARD_PATH) as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error reading leaderboard: {e}")
        return None


def format_event_name(key: str) -> str:
    parts = key.split("#")
    formatted_parts = []
    for part in parts:
        part = re.sub(r"([a-zA-Z])([0-9])", r"\1 \2", part)
        part = part.capitalize()
        formatted_parts.append(part)
    return " - ".join(formatted_parts)


def format_leaderboard(data):
    if not data:
        return "No leaderboard data found."
    event_key = list(data.keys())[0]
    event_name = format_event_name(event_key)
    entries = data[event_key]
    msg = f"**🏁 {event_name} 🏁**\n"
    for i, entry in enumerate(entries, 1):
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


def save_msg_id(msg_id):
    try:
        with open(LEADERBOARD_MSG_ID_PATH, "w") as f:
            f.write(str(msg_id))
    except Exception as e:
        print(f"Error saving message ID: {e}")


def load_msg_id():
    if os.path.exists(LEADERBOARD_MSG_ID_PATH):
        try:
            with open(LEADERBOARD_MSG_ID_PATH) as f:
                return int(f.read().strip())
        except Exception:
            return None
    return None


# --- Watcher Task ---
@tasks.loop(seconds=5)
async def check_leaderboard():
    global last_hash
    try:
        current_hash = get_file_hash(LEADERBOARD_PATH)
        if not current_hash or current_hash == last_hash:
            return

        # Wait briefly to ensure file write is complete
        await asyncio.sleep(2)
        new_hash = get_file_hash(LEADERBOARD_PATH)
        if new_hash != current_hash:
            return  # file changed again; wait for next cycle

        last_hash = current_hash
        data = read_leaderboard()
        if not data:
            return

        channel = bot.get_channel(CHANNEL_ID)
        event_key = list(data.keys())[0]
        event_name = format_event_name(event_key)
        msg_text = format_leaderboard(data)

        # --- Search for a message that matches this event ---
        async for message in channel.history(limit=20):
            if (
                message.author == bot.user
                and event_name in message.content
            ):
                await message.edit(content=msg_text)
                print(f"✏️ Edited existing leaderboard for {event_name}")
                return

        # --- If not found, post a new one ---
        await channel.send(msg_text)
        print(f"🆕 Posted new leaderboard for {event_name}")

    except Exception as e:
        print(f"Error checking leaderboard: {e}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    check_leaderboard.start()


bot.run(DISCORD_TOKEN)

