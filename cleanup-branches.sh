#!/bin/bash
# cleanup-branches.sh - Non-interactive version for WinningCV
# Run this after reviewing git branch -a

echo "=== WinningCV Branch Cleanup ==="
echo "Current branch: $(git branch --show-current)"

BRANCHES=(
  "docs/configurable-auth-backend"
  "feat/application-workspace-mvp"
  "feat/product-telemetry-funnel-analytics"
  "fix/case-insensitive-country-validation"
  "hotfix/unpin-chromium-packages"
  "migration/postgres-storage-backend"
  "wip/jack-ubuntu-api-enhancement-20260706"
)

echo "Deleting remote branches..."
for branch in "${BRANCHES[@]}"; do
  if git branch -r | grep -q "origin/$branch"; then
    git push origin --delete "$branch" 2>/dev/null && echo "  ✓ Deleted origin/$branch" || echo "  ✗ Failed to delete origin/$branch"
  else
    echo "  ✗ origin/$branch not found"
  fi
done

echo "Deleting local branches..."
for branch in "${BRANCHES[@]}"; do
  if git branch | grep -q "$branch"; then
    git branch -D "$branch" 2>/dev/null && echo "  ✓ Deleted $branch" || echo "  ✗ Failed to delete $branch"
  fi
done

echo "Cleanup complete!"
git branch -a
EOF
chmod +x cleanup-branches.sh
echo "Script updated for non-interactive use"