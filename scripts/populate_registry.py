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
intents.message_content = True
client = discord.Client(intents=intents)

registry = {}

# --- UTILS ---
def save_registry():
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)
    print(f"Saved registry.json with {len(registry)} entries")


def extract_text_from_message(msg):
    """
    Extracts readable text from:
      - normal message content
      - embeds (title, description, fields)
    """
    parts = []

    # Raw text content
    if msg.content:
        parts.append(msg.content)

    # Embed content
    for embed in msg.embeds:
        if embed.title:
            parts.append(embed.title)
        if embed.description:
            parts.append(embed.description)
        for field in embed.fields:
            parts.append(f"{field.name} {field.value}")

    # Join all detected text
    return "\n".join(parts).strip()

def parse_registry_message(msg):
    text = extract_text_from_message(msg)
    if not text:
        return None

    # Pattern: "steam - real name" or "steam — real name"
    m = re.match(r"(.+?)\s*[-—]\s*(.+)", text)
    if m:
        steam = m.group(1).strip()
        real = m.group(2).strip()
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
        extracted = extract_text_from_message(msg)
        print("[DEBUG EXTRACTED]:", repr(extracted))

        parsed = parse_registry_message(msg)
        if parsed:
            steam, real = parsed
            registry[steam] = real
            print(f"[MATCH] {steam} -> {real}")
        else:
            print("[NO MATCH]")

    save_registry()
    await client.close()


client.run(DISCORD_TOKEN)
