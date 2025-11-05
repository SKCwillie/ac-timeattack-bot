#!/bin/bash

# Export ENV variables
set -a
source ~/ac-timeattack-bot/.env
set +a


# Rotate log if it exceeds MAX_LOG_LINES
if [ -f "$LOG_FILE" ] && [ $(wc -l < "$LOG_FILE") -gt $MAX_LOG_LINES ]; then
    mv "$LOG_FILE" "$LOG_FILE.old"
fi

# Timestamp for this run
echo "Sync run at $(date)" >> "$LOG_FILE"

# Sync results to S3
$AWS_CLI s3 sync "$RESULTS_DIR" "$S3_BUCKET" --exact-timestamps >> "$LOG_FILE" 2>&1
