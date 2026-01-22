#!/bin/bash
# =============================================================================
# Job Runner with Pre-flight Session Validation
# =============================================================================
# This script validates LinkedIn session before running the job.
# If session is invalid, it sends an alert and skips the job.
#
# Usage in crontab:
#   0 9 * * * cd ~/winning-cv && ./scripts/run_job_with_validation.sh >> cron_job_runner.log 2>&1
#
# Or with docker-compose directly:
#   0 9 * * * cd ~/winning-cv && docker-compose run --rm job-runner python -c "from job_sources.linkedin_cookie_health import validate_session_for_job; valid, msg = validate_session_for_job(); exit(0 if valid else 1)" && docker-compose run --rm job-runner >> cron_job_runner.log 2>&1
# =============================================================================

set -e

cd "$(dirname "$0")/.." || exit 1

echo "=============================================="
echo "WinningCV Job Runner - $(date)"
echo "=============================================="

# Step 1: Validate LinkedIn session before running the job
echo "[$(date)] Step 1: Validating LinkedIn session..."

VALIDATION_RESULT=$(docker-compose run --rm job-runner python -c "
from job_sources.linkedin_cookie_health import validate_session_for_job
import sys
valid, msg = validate_session_for_job()
print(f'VALID={valid}')
print(f'MESSAGE={msg}')
sys.exit(0 if valid else 1)
" 2>&1) || VALIDATION_EXIT_CODE=$?

echo "$VALIDATION_RESULT"

# Extract validation result
if echo "$VALIDATION_RESULT" | grep -q "VALID=True"; then
    echo "[$(date)] Session validation PASSED. Proceeding with job..."
else
    echo "[$(date)] Session validation FAILED. Skipping job run."
    echo "[$(date)] Alert should have been sent via Telegram/Email."
    echo "=============================================="
    exit 1
fi

# Step 2: Run the actual job
echo "[$(date)] Step 2: Running job..."
docker-compose run --rm job-runner

echo "[$(date)] Job completed successfully."
echo "=============================================="
