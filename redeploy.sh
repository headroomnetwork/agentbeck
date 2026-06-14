#!/usr/bin/env bash
#
# redeploy.sh — push repo code to the live Agent Beck launchd service.
#
# Why this exists: macOS blocks launchd background services from reading the
# Google-Drive-synced repo tree (TCC / Full Disk Access). So the service runs
# from a COPY at ~/.agentbeck/app/, and the repo is the source of truth. After
# any change to main.py / db.py / static, run this to sync the copy and restart
# the service. One command instead of a fragile cp + bootout + bootstrap dance.
#
# Usage:  ./redeploy.sh
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.agentbeck/app"
LABEL="network.headroom.agentbeck"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
GUI="gui/$(id -u)"
HEALTH="http://127.0.0.1:8000/health"

echo "▶ Syncing code: repo → ${APP_DIR}"
mkdir -p "$APP_DIR"
# Copy the app code only. NEVER copy the DB (it lives at ~/.agentbeck/agentbeck.db),
# the venv, git metadata, planning docs, or caches.
rsync -a --delete \
  --include='main.py' \
  --include='db.py' \
  --include='security.py' \
  --include='ratelimit.py' \
  --include='mcp_server.py' \
  --include='seed_bugs.json' \
  --include='static/***' \
  --include='control_plane/***' \
  --include='harvest/***' \
  --exclude='*' \
  "$REPO_DIR"/ "$APP_DIR"/
echo "  synced: core app, static/, control_plane/, harvest/"

echo "▶ Restarting service ${LABEL}"
# bootout is asynchronous — bootstrapping immediately after races the still-dying
# label and fails with "Bootstrap failed: 5: Input/output error", which would
# leave the service DOWN. So: bootout, wait for the label to actually clear, then
# bootstrap with retries.
launchctl bootout "$GUI/$LABEL" 2>/dev/null || true
for _ in $(seq 1 8); do
  launchctl print "$GUI/$LABEL" >/dev/null 2>&1 || break
  sleep 1
done
bootstrapped=""
for attempt in $(seq 1 8); do
  if launchctl bootstrap "$GUI" "$PLIST" 2>/dev/null; then bootstrapped="yes"; break; fi
  echo "  bootstrap attempt ${attempt} lost the race, retrying..."
  sleep 1
done
if [ -z "$bootstrapped" ]; then
  echo "✗ Could not bootstrap ${LABEL} after 8 attempts." >&2
  echo "  Recover manually: launchctl bootstrap ${GUI} ${PLIST}" >&2
  exit 1
fi

echo "▶ Waiting for service to answer ${HEALTH}"
for i in $(seq 1 10); do
  if curl -fs --max-time 3 "$HEALTH" >/dev/null 2>&1; then
    echo "✓ Redeploy complete — service healthy: $(curl -s "$HEALTH")"
    exit 0
  fi
  sleep 1
done

echo "✗ Service did not answer ${HEALTH} within 10s — check logs at ~/.agentbeck/logs/" >&2
exit 1
