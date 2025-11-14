import os
import json
import re
import discord
from dotenv import load_dotenv
from pathlib import Path

# --- CONFIG ---
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
REGISTRY_CHANNEL_ID = int(os.getenv("REGISTRY_CHANNEL_ID"))
REGISTRY_PATH = Path(os.getenv("REGISTRY_PATH"))

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

registry = {}

# --- UTILS ---
def save_registry():
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)
    print(f"Saved registry.json with {len(registry)} entries")


def parse_registry_message(content: str):
    """
    Expected format:
        steam name - real name
        steam_name — Real Name
    Supports different dash variations.
    """
    pattern = r"(.+?)\s*[-—]\s*(.+)"
    match = re.match(pattern, content.strip())
    if match:
        steam = match.group(1).strip()
        real = match.group(2).strip()
        return steam, real
    return None


@client.event
async def on_ready():
    print(f"Connected as {client.user}")
    channel = client.get_channel(REGISTRY_CHANNEL_ID)

    if not channel:
        print("❌ Invalid REGISTRY_CHANNEL_ID")
        await client.close()
        return

    print(f"📥 Reading messages from #{channel.name}...")

    async for msg in channel.history(limit=None):
        parsed = parse_registry_message(msg.content)
        if parsed:
            steam, real = parsed
            registry[steam] = real

    save_registry()
    await client.close()


client.run(DISCORD_TOKEN)
