import os
import time
import json
import re
import discord
from discord.ext import tasks
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
LEADERBOARD_PATH = os.getenv("LEADERBOARD_PATH")

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

last_modified = 0

# --- Helper ---
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
        # Insert space between letters and digits (Season1 → Season 1)
        part = re.sub(r"([a-zA-Z])([0-9])", r"\1 \2", part)
        # Capitalize first letter
        part = part.capitalize()
        formatted_parts.append(part)

    return " - ".join(formatted_parts)

def format_leaderboard(data):
    # Expecting only one key (like "season1#week1")
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

# --- Watcher Task ---
@tasks.loop(seconds=5)
async def check_leaderboard():
    global last_modified
    try:
        mtime = os.path.getmtime(LEADERBOARD_PATH)
        if mtime != last_modified:
            last_modified = mtime
            data = read_leaderboard()
            if data:
                channel = bot.get_channel(CHANNEL_ID)
                msg = format_leaderboard(data)
                await channel.send(msg)
                print("Posted updated leaderboard to Discord.")
    except Exception as e:
        print(f"Error checking leaderboard: {e}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    check_leaderboard.start()

bot.run(DISCORD_TOKEN)

