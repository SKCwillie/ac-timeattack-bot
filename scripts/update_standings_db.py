import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import boto3
import pandas as pd
from decimal import Decimal
from datetime import datetime
from dotenv import load_dotenv
from boto3.dynamodb.conditions import Key
from logs.logger import logger
from update_standings import load_season_events
from build_leaderboard import fetch_items_for_event
from calculate_event_points import event_points

# ---------------------------------------------------------
# Configs
# ---------------------------------------------------------
load_dotenv("/home/ubuntu/ac-timeattack-bot/.env")
LAP_TABLE = os.getenv("TABLE_NAME")
STANDINGS_TABLE = os.getenv("STANDINGS_TABLE")
SEASON_CONFIG_PATH = os.getenv("SEASON_CONFIG_PATH")
dynamodb = boto3.resource("dynamodb")
lap_table = dynamodb.Table(LAP_TABLE)
standings_table = dynamodb.Table(STANDINGS_TABLE)



# ---------------------------------------------------------
# Step 1: Pick best lap per driver
# ---------------------------------------------------------
def get_best_laps_df(raw_laps):
    if not raw_laps:
        return pd.DataFrame()

    df = pd.DataFrame(raw_laps)

    # convert lap_ms to float for math
    df["lap_ms"] = df["lapTime"].astype(float)

    # Best lap per driverGuid = min lap_ms
    best_df = df.loc[df.groupby("driverGuid")["lap_ms"].idxmin()].copy()

    return best_df


# ---------------------------------------------------------
# Step 2: Identify weekly winner + calculate scoring
# ---------------------------------------------------------
def apply_scoring(best_df):
    """
    Applies your formula:

        points = 101 * (winner_time / driver_time)

    Winner is the FASTEST best-lap among all drivers.
    """
    if best_df.empty:
        return best_df

    # Determine winner lap in seconds
    fastest_ms = best_df["lap_ms"].min()
    winner_time = fastest_ms / 1000.0

    # Calculate driver lap in seconds
    best_df["lap_sec"] = best_df["lap_ms"] / 1000.0

    # Apply formula
    best_df["points"] = event_points(winner_time, best_df["lap_sec"])
    return best_df


# ---------------------------------------------------------
# Step 3: Write weekly standings into Dynamo
# PK = season
# SK = resultKey = driverGuid#eventId
# ---------------------------------------------------------
def write_week(event_key, season_id, event_index, df):
    for _, row in df.iterrows():

        driver_guid = row["driverGuid"]
        driver_name = row["driverName"]
        result_key = f"{driver_guid}#{event_key}"

        standings_table.put_item(
            Item={
                "season": season_id,
                "resultKey": result_key,

                "driverGuid": driver_guid,
                "driverName": driver_name,

                "eventId": event_key,
                "eventIndex": event_index,

                "lap_ms": Decimal(str(row["lap_ms"])),
                "points": Decimal(str(row["points"])),

                "timestamp": datetime.utcnow().isoformat()
            }
        )


# ---------------------------------------------------------
# MAIN RUNNER
# ---------------------------------------------------------
def update_standings(season_id="season1"):
    events = load_season_events()

    for idx, event_key in enumerate(events, start=1):
        event_id = f"{season_id}#{event_key}"
        logger.info(f"\n 🔁 Processing {event_id} ...")

        # 1. Load raw laps
        raw_laps = fetch_items_for_event(event_id)
        if not raw_laps:
            logger.error(" ❌ - No laps found")
            continue

        # 2. Best lap per driver
        best_df = get_best_laps_df(raw_laps)

        # 3. Calculate scoring relative to weekly winner
        best_df = apply_scoring(best_df)

        # 4. Store into Standings table
        write_week(event_key, season_id, idx, best_df)

        print(f" - Stored {len(best_df)} results into Standings")


if __name__ == "__main__":
    update_standings("season1")
