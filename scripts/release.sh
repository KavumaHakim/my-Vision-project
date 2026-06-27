#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# Vision V1 — build frontend, commit dist, push
# Run on your DEV machine instead of `git push`:  bash scripts/release.sh
#
# The Pi serves the committed frontend/dist (no Node on the Pi), so the build
# must happen here and be committed before pushing. This script makes that
# impossible to forget. After it runs, deploy on the Pi with:
#     bash scripts/update.sh
# ---------------------------------------------------------------------------

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$REPO_DIR/frontend"

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "node_modules missing — installing deps first..."
  (cd "$FRONTEND_DIR" && npm install)
fi

echo "Building frontend..."
(cd "$FRONTEND_DIR" && npm run build)

# Stage the build output (-A so deleted/renamed asset files are picked up too)
git -C "$REPO_DIR" add -A frontend/dist

if git -C "$REPO_DIR" diff --cached --quiet -- frontend/dist; then
  echo "Frontend dist unchanged — no new build to commit."
else
  echo "Committing rebuilt frontend dist..."
  git -C "$REPO_DIR" commit -m "Build frontend dist"
fi

# Warn about any OTHER tracked changes that won't be included in this push
if ! git -C "$REPO_DIR" diff --quiet || ! git -C "$REPO_DIR" diff --cached --quiet; then
  echo ""
  echo "WARNING: you have uncommitted changes that will NOT be pushed:"
  git -C "$REPO_DIR" status --short
  echo "Commit them first if they should ship, then re-run this script."
  echo ""
fi

echo "Pushing..."
git -C "$REPO_DIR" push

echo ""
echo "Done. Now deploy on the Pi:  bash scripts/update.sh"
