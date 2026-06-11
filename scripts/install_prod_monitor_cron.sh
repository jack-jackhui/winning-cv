#!/usr/bin/env bash
# Idempotently install the WinningCV production monitor cron entry.
# This script preserves all existing crontab lines and only replaces the
# marked WinningCV block below.
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/home/azureuser/winning-cv}"
SCHEDULE="${SCHEDULE:-*/5 * * * *}"
LOG_DIR="${LOG_DIR:-$DEPLOY_DIR/logs}"
BACKUP_DIR="${BACKUP_DIR:-$LOG_DIR/crontab-backups}"
BEGIN_MARKER="# BEGIN WinningCV prod monitor"
END_MARKER="# END WinningCV prod monitor"
CRON_LINE="$SCHEDULE cd $DEPLOY_DIR && ./scripts/prod_monitor_cron.sh"

mkdir -p "$BACKUP_DIR"
current="$(mktemp)"
next="$(mktemp)"
trap 'rm -f "$current" "$next"' EXIT

crontab -l > "$current" 2>/dev/null || true
cp "$current" "$BACKUP_DIR/crontab.$(date +%Y%m%dT%H%M%SZ)"

awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" '
  $0 == begin { skip=1; next }
  $0 == end { skip=0; next }
  !skip { print }
' "$current" > "$next"

{
  cat "$next"
  printf "\n%s\n%s\n%s\n" "$BEGIN_MARKER" "$CRON_LINE" "$END_MARKER"
} | crontab -

echo "Installed WinningCV production monitor cron: $CRON_LINE"
