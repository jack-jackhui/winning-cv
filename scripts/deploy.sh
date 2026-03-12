#!/bin/bash
# =============================================================================
# WinningCV Deployment Script
# =============================================================================
# Usage: ./deploy.sh
# Pulls latest images and restarts services with health check validation
# =============================================================================

set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-$HOME/winning-cv}"
HEALTH_URL="http://localhost:13000/health"
HEALTH_TIMEOUT=30
PRUNE_AGE="168h"  # 7 days

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "🚀 Starting WinningCV deployment..."
cd "$DEPLOY_DIR"

# Pull latest images
log "📥 Pulling latest images..."
docker compose pull

# Start/restart services
log "🔄 Restarting services..."
docker compose up -d --remove-orphans

# Wait for health check
log "⏳ Waiting for health check (max ${HEALTH_TIMEOUT}s)..."
for i in $(seq 1 $HEALTH_TIMEOUT); do
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        log "✅ Health check passed!"
        break
    fi
    if [ $i -eq $HEALTH_TIMEOUT ]; then
        log "❌ Health check failed after ${HEALTH_TIMEOUT}s"
        log "📋 Container logs:"
        docker compose logs --tail=50
        exit 1
    fi
    sleep 1
done

# Cleanup old images
log "🧹 Pruning old images (older than $PRUNE_AGE)..."
docker image prune -af --filter "until=$PRUNE_AGE"

log "🎉 Deployment completed successfully!"
