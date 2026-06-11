#!/usr/bin/env bash
# Cron wrapper for scripts/prod_monitor.sh.
# - Logs every run to logs/prod_monitor_cron.log
# - Sends Telegram only on monitor failure when TELEGRAM_BOT_TOKEN and
#   TELEGRAM_CHAT_ID are present in .env or the process environment
# - Rate-limits failure alerts to avoid repeated cron spam
set -uo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/home/azureuser/winning-cv}"
LOG_DIR="${LOG_DIR:-$DEPLOY_DIR/logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/prod_monitor_cron.log}"
STATE_DIR="${STATE_DIR:-$LOG_DIR}"
LOCK_FILE="${LOCK_FILE:-/tmp/winningcv-prod-monitor.lock}"
ALERT_COOLDOWN_SECONDS="${ALERT_COOLDOWN_SECONDS:-3600}"
ENV_FILE="${ENV_FILE:-$DEPLOY_DIR/.env}"

mkdir -p "$LOG_DIR" "$STATE_DIR"

get_env_value() {
  local key="$1"
  local current="${!key:-}"
  if [ -n "$current" ]; then
    printf "%s" "$current"
    return 0
  fi
  if [ -f "$ENV_FILE" ]; then
    python3 - "$ENV_FILE" "$key" <<'PY'
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
key = sys.argv[2]
for line in env_path.read_text(errors="ignore").splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    name, value = stripped.split("=", 1)
    if name.strip() == key:
        value = value.strip().strip('"').strip("'")
        print(value, end="")
        break
PY
  fi
}

send_telegram_alert() {
  local message="$1"
  local token chat_id
  token="$(get_env_value TELEGRAM_BOT_TOKEN)"
  chat_id="$(get_env_value TELEGRAM_CHAT_ID)"

  if [ -z "$token" ] || [ -z "$chat_id" ]; then
    echo "[$(date -Is)] alert delivery skipped: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not configured"
    return 0
  fi

  TELEGRAM_BOT_TOKEN="$token" TELEGRAM_CHAT_ID="$chat_id" ALERT_MESSAGE="$message" python3 - <<'PY'
import os
import urllib.parse
import urllib.request

url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
data = urllib.parse.urlencode({
    "chat_id": os.environ["TELEGRAM_CHAT_ID"],
    "text": os.environ["ALERT_MESSAGE"],
    "disable_web_page_preview": "true",
}).encode()
urllib.request.urlopen(url, data=data, timeout=10).read()
PY
}

{
  flock -n 9 || { echo "[$(date -Is)] previous monitor run still active; skipping"; exit 0; }

  started_at="$(date -Is)"
  echo "[$started_at] starting WinningCV production monitor"

  output="$(cd "$DEPLOY_DIR" && ./scripts/prod_monitor.sh 2>&1)"
  status=$?
  printf "%s\n" "$output"

  if [ "$status" -ne 0 ]; then
    now_epoch="$(date +%s)"
    state_file="$STATE_DIR/prod_monitor_last_alert.epoch"
    last_epoch="0"
    [ -f "$state_file" ] && last_epoch="$(cat "$state_file" 2>/dev/null || echo 0)"

    if [ $((now_epoch - last_epoch)) -ge "$ALERT_COOLDOWN_SECONDS" ]; then
      host="$(hostname -f 2>/dev/null || hostname)"
      alert="❌ WinningCV production monitor failed on $host at $(date -Is)\n\n$output"
      if send_telegram_alert "$alert"; then
        echo "$now_epoch" > "$state_file"
        echo "[$(date -Is)] failure alert sent"
      else
        echo "[$(date -Is)] failure alert attempt failed"
      fi
    else
      echo "[$(date -Is)] failure alert suppressed by ${ALERT_COOLDOWN_SECONDS}s cooldown"
    fi
    exit "$status"
  fi

  echo "[$(date -Is)] monitor completed successfully"
} 9>"$LOCK_FILE" >>"$LOG_FILE" 2>&1
