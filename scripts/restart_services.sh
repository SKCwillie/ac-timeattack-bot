#!/bin/bash
SERVICES=(
  assetto-corsa-server
  update-dynamo-db
  event-watcher
  discord-leaderboard
  discord-schedule
  discord-standings
)

for svc in "${SERVICES[@]}"; do
  echo "Restarting $svc..."
  sudo systemctl restart "$svc"
done

