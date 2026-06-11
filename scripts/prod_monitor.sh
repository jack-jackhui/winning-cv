#!/usr/bin/env bash
set -euo pipefail
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:13001}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-winning-cv-postgres}"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
MAX_PENDING="${MAX_PENDING:-20}"
MAX_FAILED_24H="${MAX_FAILED_24H:-0}"
MIN_FREE_PCT="${MIN_FREE_PCT:-10}"
problems=()
check() { if ! eval "$1" >/dev/null 2>&1; then problems+=("$2"); fi; }
check "curl -fsS '$FRONTEND_URL/health'" "frontend health endpoint failed"
check "curl -fsS '$FRONTEND_URL/api/health'" "API health endpoint failed"
for c in winning-cv-frontend winning-cv-api winning-cv-worker winning-cv-postgres winning-cv-minio; do
  state="$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || echo missing)"
  [ "$state" = running ] || problems+=("$c not running: $state")
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$c" 2>/dev/null || echo missing)"
  if [ "$health" != none ] && [ "$health" != healthy ]; then problems+=("$c health=$health"); fi
done
pending="$(docker exec "$POSTGRES_CONTAINER" psql -U winningcv -d winningcv -Atc "select count(*) from task_queue where state='pending';" 2>/dev/null || echo 0)"
running="$(docker exec "$POSTGRES_CONTAINER" psql -U winningcv -d winningcv -Atc "select count(*) from task_queue where state='running';" 2>/dev/null || echo 0)"
failed="$(docker exec "$POSTGRES_CONTAINER" psql -U winningcv -d winningcv -Atc "select count(*) from task_queue where state='failed' and updated_at > now() - interval '24 hours';" 2>/dev/null || echo 0)"
[ "${pending:-0}" -le "$MAX_PENDING" ] || problems+=("queue pending=$pending > $MAX_PENDING")
[ "${failed:-0}" -le "$MAX_FAILED_24H" ] || problems+=("queue failed_24h=$failed > $MAX_FAILED_24H")
free_pct="$(df -P . | awk 'NR==2 {print 100-$5}' | tr -d '%')"
[ "${free_pct:-0}" -ge "$MIN_FREE_PCT" ] || problems+=("disk free ${free_pct}% < ${MIN_FREE_PCT}%")
if [ "${#problems[@]}" -gt 0 ]; then
  msg="WinningCV monitor FAILED: ${problems[*]} | queue pending=$pending running=$running failed24h=$failed disk_free=${free_pct}%"
  echo "$msg" >&2
  if [ -n "$ALERT_WEBHOOK" ]; then
    MONITOR_MSG="$msg" python3 - <<'PY'
import json, os, urllib.request
msg = os.environ.get('MONITOR_MSG')
req = urllib.request.Request(os.environ['ALERT_WEBHOOK'], data=json.dumps({'text': msg}).encode(), headers={'Content-Type':'application/json'})
urllib.request.urlopen(req, timeout=10).read()
PY
  fi
  exit 1
fi
echo "WinningCV monitor OK | queue pending=$pending running=$running failed24h=$failed disk_free=${free_pct}%"
