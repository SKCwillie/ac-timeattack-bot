import sys, os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
import json
import time
import hashlib
import discord
from discord.ext import tasks
from dotenv import load_dotenv

from bot.logger import logger

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
STANDINGS_CHANNEL_ID = int(os.getenv("STANDINGS_CHANNEL"))
SEASON_STANDINGS_PATH = os.getenv("SEASON_STANDINGS_PATH")
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
last_hash = None


def file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


def format_standings(data):
    season = data.get("season", "?")
    standings = data.get("standings", [])
    msg = f"**📊 Season {season} Standings 📊**\n\n"
    for i, row in enumerate(standings, 1):
        msg += f"{i}. {row['driver']} — {row['points']} pts\n"
    return msg + "\n"


@bot.event
async def on_ready():
    logger.info("[standings] Bot online")
    watch_standings.start()


@tasks.loop(seconds=5)
async def watch_standings():
    global last_hash

    h = file_hash(SEASON_STANDINGS_PATH)
    if not h or h == last_hash:
        return

    last_hash = h

    with open(SEASON_STANDINGS_PATH) as f:
        data = json.load(f)

    msg = format_standings(data)
    channel = bot.get_channel(STANDINGS_CHANNEL)
    logger.info("[standings] ✉️ Posting NEW standings message")
    await channel.send(msg)


bot.run(os.getenv("DISCORD_TOKEN"))
