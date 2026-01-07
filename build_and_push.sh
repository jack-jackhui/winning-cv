#!/bin/zsh
set -euo pipefail

# =============================================================================
# WinningCV Docker Build & Push Script
# =============================================================================
# Usage:
#   ./build_and_push.sh           # Build and push ALL images
#   ./build_and_push.sh backend   # Build and push backend only
#   ./build_and_push.sh frontend  # Build and push frontend only
#   ./build_and_push.sh all       # Build and push ALL images
# =============================================================================

# Load environment variables
source .env.build_config

# Variables
IMAGE_NAME="winning-cv"
VERSION_TAG="latest"
FRONTEND_TAG="frontend"
GHCR_URL="ghcr.io/${GITHUB_USER}/${IMAGE_NAME}"

# Parse command line argument
BUILD_TARGET="${1:-all}"

# Validate argument
if [[ ! "$BUILD_TARGET" =~ ^(all|backend|frontend)$ ]]; then
    echo "Error: Invalid argument '$BUILD_TARGET'"
    echo ""
    echo "Usage: $0 [all|backend|frontend]"
    echo "  all      - Build and push both backend and frontend (default)"
    echo "  backend  - Build and push backend image only"
    echo "  frontend - Build and push frontend image only"
    exit 1
fi

# Login to GitHub Container Registry
echo "Logging into GitHub Container Registry..."
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin

# Function to build backend
build_backend() {
    local BACKEND_IMAGE="${GHCR_URL}:${VERSION_TAG}"
    echo ""
    echo "=========================================="
    echo "Building Backend Image (Python/FastAPI)..."
    echo "=========================================="
    echo "Target image: ${BACKEND_IMAGE}"
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --target backend \
        -t "${BACKEND_IMAGE}" \
        . --push

    echo "Backend image pushed: ${BACKEND_IMAGE}"
}

# Function to build frontend
build_frontend() {
    local FRONTEND_IMAGE="${GHCR_URL}:${FRONTEND_TAG}"
    echo ""
    echo "=========================================="
    echo "Building Frontend Image (React/Nginx)..."
    echo "=========================================="
    echo "Target image: ${FRONTEND_IMAGE}"
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --target frontend \
        -t "${FRONTEND_IMAGE}" \
        . --push

    echo "Frontend image pushed: ${FRONTEND_IMAGE}"
}

# Execute based on target
case "$BUILD_TARGET" in
    backend)
        build_backend
        ;;
    frontend)
        build_frontend
        ;;
    all)
        build_backend
        build_frontend
        ;;
esac

echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="
echo ""
echo "Images available:"
if [[ "$BUILD_TARGET" == "all" || "$BUILD_TARGET" == "backend" ]]; then
    echo "  - ${GHCR_URL}:${VERSION_TAG} (Backend/CLI)"
fi
if [[ "$BUILD_TARGET" == "all" || "$BUILD_TARGET" == "frontend" ]]; then
    echo "  - ${GHCR_URL}:${FRONTEND_TAG} (Frontend)"
fi
