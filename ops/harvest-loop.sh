#!/bin/sh
# Daily harvest driver for the cron container.
#
# A plain sleep loop rather than crond: this image has no cron daemon, and
# crond would need the database credentials plumbed into the job's
# environment separately. Here the harvest simply inherits the container's.
set -u
AT="${HARVEST_AT:-08:15}"

echo "[harvest-loop] daily harvest at ${AT} UTC"
while true; do
    now=$(date -u +%s)
    target=$(date -u -d "today ${AT}" +%s)
    [ "$target" -le "$now" ] && target=$((target + 86400))
    echo "[harvest-loop] next run $(date -u -d "@${target}" +%FT%TZ), sleeping $((target - now))s"
    sleep $((target - now))
    echo "[harvest-loop] starting $(date -u +%FT%TZ)"
    python /app/harvest.py || echo "[harvest-loop] harvest exited $?"
done
