#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# Vision V1 — pull latest and restart
# Run on Pi after pushing from dev machine: bash scripts/update.sh
# ---------------------------------------------------------------------------

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Pulling latest..."
git -C "$REPO_DIR" pull

echo "Restarting backend..."
sudo systemctl restart vision-backend.service

echo "Done. Tunnel keeps running — URL unchanged."
sudo systemctl status vision-backend.service --no-pager -l
