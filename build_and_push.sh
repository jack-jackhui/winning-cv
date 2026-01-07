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
GHCR_URL="ghcr.io/$GITHUB_USER/$IMAGE_NAME"

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
    echo ""
    echo "=========================================="
    echo "Building Backend Image (Python/FastAPI)..."
    echo "=========================================="
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --target backend \
        -t "$GHCR_URL:$VERSION_TAG" \
        . --push

    echo "Backend image pushed: $GHCR_URL:$VERSION_TAG"
}

# Function to build frontend
build_frontend() {
    echo ""
    echo "=========================================="
    echo "Building Frontend Image (React/Nginx)..."
    echo "=========================================="
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --target frontend \
        -t "$GHCR_URL:frontend" \
        . --push

    echo "Frontend image pushed: $GHCR_URL:frontend"
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
    echo "  - $GHCR_URL:$VERSION_TAG (Backend/CLI)"
fi
if [[ "$BUILD_TARGET" == "all" || "$BUILD_TARGET" == "frontend" ]]; then
    echo "  - $GHCR_URL:frontend (Frontend)"
fi
