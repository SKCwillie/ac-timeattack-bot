import json
import boto3
import discord
from discord.ext import tasks, commands
import os

# --- CONFIG ---
S3_BUCKET = "acserver-results"
REGION = "us-east-1"
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # ensure it's an int
PROCESSED_FILES_PATH = "processed_files.json"

# --- AWS + Discord setup ---
s3 = boto3.client("s3", region_name=REGION)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- In-memory state ---
leaderboard = {}         # {(track, car): {driver: best_lap}}
leaderboard_msg_id = None # Discord message ID
processed_files = set()   # files already processed

# --- Load previously processed files ---
if os.path.exists(PROCESSED_FILES_PATH):
    with open(PROCESSED_FILES_PATH) as f:
        processed_files = set(json.load(f))
else:
    processed_files = set()

# --- Utility functions ---

def escape_markdown(text: str) -> str:
    """Escape Discord markdown characters so usernames render literally."""
    for ch in ('*', '_', '~', '`', '|', '>'):
        text = text.replace(ch, f'\\{ch}')
    return text

def ms_to_time(ms):
    mins = ms // 60000
    secs = (ms // 1000) % 60
    millis = ms % 1000
    return f"{mins}:{secs:02}.{millis:03}"

def parse_result_file(data):
    track = data.get("TrackName", "unknown")
    results = data.get("Result", [])
    for car in results:
        driver = car.get("DriverName")
        model = car.get("CarModel")
        best = car.get("BestLap", 0)
        if driver and best > 0 and best < 999999999:
            key = (track, model)
            if key not in leaderboard:
                leaderboard[key] = {}
            if driver not in leaderboard[key] or best < leaderboard[key][driver]:
                leaderboard[key][driver] = best

def build_leaderboard_text():
    lines = []
    for (track, model), drivers in leaderboard.items():
        lines.append(f"🏁 **{escape_markdown(track)}** | {escape_markdown(model)}")
        sorted_drivers = sorted(drivers.items(), key=lambda x: x[1])
        for i, (driver, best) in enumerate(sorted_drivers, start=1):
            safe_driver = escape_markdown(driver.strip())  # ✅ sanitize here
            lines.append(f"{i}. {safe_driver} — {ms_to_time(best)}")
        lines.append("")  # blank line between sections
    return "\n".join(lines) or "No results yet."

def save_processed_files():
    with open(PROCESSED_FILES_PATH, "w") as f:
        json.dump(list(processed_files), f)

# --- Main S3 processing and Discord update task ---
@tasks.loop(seconds=60)
async def check_s3_and_update():
    global leaderboard_msg_id
    try:
        resp = s3.list_objects_v2(Bucket=S3_BUCKET)
        if "Contents" not in resp:
            return

        new_file_found = False
        for item in resp["Contents"]:
            key = item["Key"]
            if key in processed_files or not key.endswith(".json"):
                continue

            # fetch and parse new file
            obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
            data = json.loads(obj["Body"].read())
            parse_result_file(data)

            processed_files.add(key)
            new_file_found = True
            print(f"Processed file: {key}")

        if new_file_found:
            save_processed_files()  # persist processed files
            text = build_leaderboard_text()
            channel = bot.get_channel(CHANNEL_ID)
            if not channel:
                print("Channel not found")
                return

            # Edit existing message if exists, else send new
            if leaderboard_msg_id:
                try:
                    msg = await channel.fetch_message(leaderboard_msg_id)
                    await msg.edit(content=text)
                except:
                    msg = await channel.send(text)
                    leaderboard_msg_id = msg.id
            else:
                msg = await channel.send(text)
                leaderboard_msg_id = msg.id

    except Exception as e:
        print(f"Error in check_s3_and_update: {e}")

# --- Bot events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await check_s3_and_update()  # run once immediately on startup
    check_s3_and_update.start()  # then start the loop

# --- Run bot ---
bot.run(DISCORD_TOKEN)

