#!/bin/bash
# =============================================================================
# WinningCV Deployment Script
# =============================================================================
# Usage: ./deploy.sh
# Pulls latest images and restarts services with health check validation
# =============================================================================

set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-$HOME/winning-cv}"
HEALTH_URL="${HEALTH_URL:-http://localhost:13001/health}"
HEALTH_TIMEOUT=30
PRUNE_AGE="168h"  # 7 days

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "🚀 Starting WinningCV deployment..."
cd "$DEPLOY_DIR"

# Validate production config before touching running services
log "🔎 Validating production config..."
./scripts/validate_prod_config.sh

# Pull latest images
log "📥 Pulling latest images..."
docker compose pull

# Apply idempotent database migrations for existing deployments
log "🗄️ Applying database migrations..."
./scripts/prod_migrate_db.sh

# Start/restart services
log "🔄 Restarting services..."
docker compose up -d --remove-orphans

# Wait for endpoint and container health checks
log "⏳ Waiting for health checks (max ${HEALTH_TIMEOUT}s)..."
for i in $(seq 1 $HEALTH_TIMEOUT); do
    frontend_health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' winning-cv-frontend 2>/dev/null || echo missing)"
    api_health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' winning-cv-api 2>/dev/null || echo missing)"
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1         && curl -sf "${HEALTH_URL%/health}/api/health" > /dev/null 2>&1         && [ "$frontend_health" = "healthy" ]         && [ "$api_health" = "healthy" ]; then
        log "✅ Health checks passed!"
        break
    fi
    if [ $i -eq $HEALTH_TIMEOUT ]; then
        log "❌ Health checks failed after ${HEALTH_TIMEOUT}s (frontend=$frontend_health api=$api_health)"
        log "📋 Container logs:"
        docker compose logs --tail=50 frontend api
        exit 1
    fi
    sleep 1
done

# Cleanup old images
log "🧹 Pruning old images (older than $PRUNE_AGE)..."
docker image prune -af --filter "until=$PRUNE_AGE"

log "🎉 Deployment completed successfully!"
