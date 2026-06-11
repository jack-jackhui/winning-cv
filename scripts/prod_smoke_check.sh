#!/usr/bin/env bash
set -euo pipefail
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:13001}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-winning-cv-postgres}"
WORKER_CONTAINER="${WORKER_CONTAINER:-winning-cv-worker}"
FRONTEND_CONTAINER="${FRONTEND_CONTAINER:-winning-cv-frontend}"
API_CONTAINER="${API_CONTAINER:-winning-cv-api}"
fail() { echo "❌ $*" >&2; exit 1; }
pass() { echo "✅ $*"; }
command -v docker >/dev/null || fail "docker not found"
docker compose -f "$COMPOSE_FILE" config >/dev/null
pass "docker compose config is valid"
curl -fsS "$FRONTEND_URL/health" >/dev/null || fail "frontend health endpoint failed: $FRONTEND_URL/health"
pass "frontend /health reachable"
curl -fsS "$FRONTEND_URL/api/health" >/dev/null || fail "API health via frontend proxy failed: $FRONTEND_URL/api/health"
pass "API /api/health reachable through frontend proxy"
for c in "$FRONTEND_CONTAINER" "$API_CONTAINER" "$WORKER_CONTAINER" "$POSTGRES_CONTAINER" winning-cv-minio; do
  state="$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || true)"
  [ "$state" = "running" ] || fail "$c is not running (state=$state)"
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$c" 2>/dev/null || true)"
  if [ "$health" != "none" ] && [ "$health" != "healthy" ]; then fail "$c health is $health"; fi
  pass "$c running${health:+ / health=$health}"
done
queue_stats="$(docker exec "$POSTGRES_CONTAINER" psql -U winningcv -d winningcv -Atc "select state || ':' || count(*) from task_queue group by state order by state;" 2>/dev/null || true)"
echo "Queue stats: ${queue_stats:-no task_queue rows}"
failed_recent="$(docker exec "$POSTGRES_CONTAINER" psql -U winningcv -d winningcv -Atc "select count(*) from task_queue where state='failed' and updated_at > now() - interval '24 hours';" 2>/dev/null || echo 0)"
[ "${failed_recent:-0}" -eq 0 ] || fail "recent failed queue tasks: $failed_recent"
pass "no failed queue tasks in last 24h"
smoke_id="smoke-$(date +%s)"
docker exec "$POSTGRES_CONTAINER" psql -U winningcv -d winningcv -v smoke_id="$smoke_id" -qAt <<'SQL' >/dev/null
INSERT INTO task_queue(task_id, task_type, payload, user_email, correlation_id)
VALUES (:'smoke_id', 'notification', '{"smoke":true}', 'smoke@winningcv.local', :'smoke_id');
SQL
for _ in $(seq 1 20); do
  state="$(docker exec "$POSTGRES_CONTAINER" psql -U winningcv -d winningcv -Atc "select state from task_queue where task_id='$smoke_id';" 2>/dev/null || true)"
  [ "$state" = "completed" ] && break
  [ "$state" = "failed" ] && fail "queue smoke task failed"
  sleep 1
done
[ "${state:-}" = "completed" ] || fail "queue smoke task did not complete (state=${state:-missing})"
pass "worker processed queue smoke task"
pass "production smoke check passed"
