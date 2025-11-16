import sys, os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
import json
import re
import time
import asyncio
import discord
from datetime import datetime
from dotenv import load_dotenv
from logs.logger import logger
from track_flags import get_track_flag
from car_flags import get_car_flag

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SCHEDULE_CHANNEL_ID = int(os.getenv("SCHEDULE_CHANNEL"))
SEASON_CONFIG_PATH = "/home/ubuntu/ac-timeattack-bot/seasonConfig.json"
LAST_MODIFIED = None
intents = discord.Intents.default()
bot = discord.Client(intents=intents)


# --- Format Track and Car Names ---
def clean_name(name: str) -> str:
    if not name:
        return ""
    name = name.replace("ks_", "")  # remove ks_
    name = name.replace("_", " ")   # convert underscores to spaces
    return name.title()             # Title Case



# --- Build the full schedule message for Discord ---
def build_schedule_text(config):
    season_num = config.get("season", "?")
    lines = [f"🏁 **Season {season_num} Schedule** 🏁\n"]

    for key, event in config.items():
        if key == "season":
            continue

        if 'preseason' in key.lower() or 'postseason' in key.lower():
            continue

        # Format date nicely
        date_obj = datetime.strptime(event["startDate"], "%Y-%m-%d")
        pretty_date = date_obj.strftime("%b %d, %Y")

        # Clean formatting
        track = clean_name(event["track"])
        track_flag = get_track_flag(track)
        track_config = clean_name(event.get("trackConfig", ""))
        cars = ", ".join(clean_name(c) for c in event["cars"])

        # Event section title
        event_title = clean_name(re.sub(r'(?<=\D)(?=\d)', ' ', key))

        lines.append(f"### 🏁  ==== {event_title} ====")
        lines.append(f"**📆 Date:**  {pretty_date}")

        if track_config:
            lines.append(f"**🏎️ Track:**  {track} {track_flag} — 🔧 {track_config}")
        else:
            lines.append(f"**🏎️ Track:**  {track} {track_flag}")

       # Add flags per car
        car_list = []
        for car in event["cars"]:
            pretty = clean_name(car)
            flag = get_car_flag(pretty)
            car_list.append(f"{pretty} {flag}")

        lines.append(f"**🚗 Cars:** {', '.join(car_list)}\n")
 
    return "\n".join(lines)



# --- Post new schedule or update existing schedule message ---
async def post_or_update_schedule():
    # Load JSON config
    with open(SEASON_CONFIG_PATH) as f:
        config = json.load(f)

    season_num = config.get("season", "?")
    schedule_text = build_schedule_text(config)

    # Get Discord channel
    channel = bot.get_channel(SCHEDULE_CHANNEL_ID)
    if channel is None:
        logger.error("❌ [Schedule Bot] Error: Could not find schedule channel")
        return

    # Search channel history for existing Season X message
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and msg.content.startswith(f"🏁 **Season {season_num} Schedule**"):
            await msg.edit(content=schedule_text)
            logger.info("✏️[Schedule Bot] Updated existing schedule message")
            return

    # No existing message → post new
    await channel.send(schedule_text)
    logger.info("🆕 [Schedule Bot] Posted NEW schedule message")

# --- Watch Season Config file for changes to schedule ---
async def watch_season_config():
    global LAST_MODIFIED

    config_path = SEASON_CONFIG_PATH
    LAST_MODIFIED = os.path.getmtime(config_path)

    await bot.wait_until_ready()
    print(f"[Watcher] Monitoring {config_path}")

    while not bot.is_closed():
        try:
            current_mtime = os.path.getmtime(config_path)

            if current_mtime != LAST_MODIFIED:
                logger.info("[Schedule Bot] Detected change in seasonConfig.json")
                LAST_MODIFIED = current_mtime

                # Rebuild and update the schedule
                await post_or_update_schedule()
                logger.info("[Schedule Bot] Schedule updated")

        except Exception as e:
            logger.error(f"[Schedule Bot] Error: {e}")

        await asyncio.sleep(10)  # check every 5 seconds



# --- Bot Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await post_or_update_schedule()

    # Start watcher task
    bot.loop.create_task(watch_season_config())

bot.run(DISCORD_TOKEN)

