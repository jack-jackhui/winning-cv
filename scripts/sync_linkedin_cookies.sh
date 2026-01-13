#!/bin/bash
# =============================================================================
# Sync LinkedIn Cookies to Production Server
# =============================================================================
# Usage:
#   ./scripts/sync_linkedin_cookies.sh              # Use default server
#   ./scripts/sync_linkedin_cookies.sh user@host    # Specify server
#   ./scripts/sync_linkedin_cookies.sh --check      # Check local cookie status
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOCAL_COOKIE_FILE="$PROJECT_ROOT/cookies/linkedin_cookies.json"

# Default production server (from CLAUDE.md: azure-vm)
DEFAULT_SERVER="azure-vm"
REMOTE_PATH="~/winning-cv/cookies/"

# Parse arguments
if [[ "${1:-}" == "--check" ]]; then
    echo "Checking local LinkedIn cookie status..."
    cd "$PROJECT_ROOT"
    python -m job_sources.linkedin_login --check
    exit 0
fi

SERVER="${1:-$DEFAULT_SERVER}"

# Check if local cookies exist
if [[ ! -f "$LOCAL_COOKIE_FILE" ]]; then
    echo "Error: No local cookies found at $LOCAL_COOKIE_FILE"
    echo ""
    echo "Run the login script first:"
    echo "  cd $PROJECT_ROOT"
    echo "  python -m job_sources.linkedin_login"
    exit 1
fi

# Display cookie info
echo "==========================================="
echo "LinkedIn Cookie Sync"
echo "==========================================="
echo "Local cookie file: $LOCAL_COOKIE_FILE"
echo "Target server:     $SERVER"
echo "Remote path:       $REMOTE_PATH"
echo ""

# Show when cookies were saved
SAVED_AT=$(python3 -c "import json; print(json.load(open('$LOCAL_COOKIE_FILE')).get('saved_at', 'Unknown'))" 2>/dev/null || echo "Unknown")
echo "Cookies saved at:  $SAVED_AT"
echo ""

# Create remote directory and sync
echo "Syncing cookies to production server..."
ssh "$SERVER" "mkdir -p $REMOTE_PATH"
scp "$LOCAL_COOKIE_FILE" "$SERVER:$REMOTE_PATH"

echo ""
echo "==========================================="
echo "SUCCESS! Cookies synced to $SERVER"
echo "==========================================="
echo ""
echo "The production scraper will now use authenticated LinkedIn access."
echo ""
echo "To verify on production:"
echo "  ssh $SERVER"
echo "  cat ~/winning-cv/cookies/linkedin_cookies.json | head -5"
