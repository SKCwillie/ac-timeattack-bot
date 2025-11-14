#!/bin/bash
SERVICES=(
  assetto-corsa-server
  update-dynamo-db
  event-watcher
  discord-leaderboard
  discord-schedule
)

for svc in "${SERVICES[@]}"; do
  echo "Restarting $svc..."
  sudo systemctl restart "$svc"
done

