#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# Vision V1 — systemd service installer
# Run once on the Pi: bash scripts/install-services.sh
# ---------------------------------------------------------------------------

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$REPO_DIR/backend"
VENV_UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"
RUN_USER="$(whoami)"

# Locate cloudflared
CLOUDFLARED="$(command -v cloudflared 2>/dev/null || true)"
if [ -z "$CLOUDFLARED" ]; then
  echo "ERROR: cloudflared not found. Install it first:"
  echo "  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o /tmp/cloudflared.deb"
  echo "  sudo dpkg -i /tmp/cloudflared.deb"
  exit 1
fi

if [ ! -f "$VENV_UVICORN" ]; then
  echo "ERROR: venv not found at $VENV_UVICORN"
  echo "Run: cd backend && python3 -m venv .venv --system-site-packages && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

echo "Installing Vision V1 services..."
echo "  Repo:        $REPO_DIR"
echo "  User:        $RUN_USER"
echo "  cloudflared: $CLOUDFLARED"
echo ""

# ---------------------------------------------------------------------------
# 1. Backend service
# ---------------------------------------------------------------------------
sudo tee /etc/systemd/system/vision-backend.service > /dev/null << EOF
[Unit]
Description=Vision V1 — FastAPI backend + frontend
After=network.target
Wants=network.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$BACKEND_DIR
ExecStart=$VENV_UVICORN main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vision-backend

[Install]
WantedBy=multi-user.target
EOF

# ---------------------------------------------------------------------------
# 2. Cloudflare tunnel service
# ---------------------------------------------------------------------------
# Auto-detect tunnel mode:
#   - If ~/.cloudflared/config.yml exists (named tunnel set up), use it ->
#     stable custom-domain URL that survives reboots.
#   - Otherwise fall back to a quick tunnel -> random trycloudflare.com URL.
TUNNEL_CONFIG="$HOME/.cloudflared/config.yml"
if [ -f "$TUNNEL_CONFIG" ]; then
  TUNNEL_EXECSTART="$CLOUDFLARED tunnel --config $TUNNEL_CONFIG run"
  echo "  tunnel:      named (config $TUNNEL_CONFIG)"
else
  TUNNEL_EXECSTART="$CLOUDFLARED tunnel --url http://localhost:8000"
  echo "  tunnel:      quick (random trycloudflare.com URL)"
fi

sudo tee /etc/systemd/system/vision-tunnel.service > /dev/null << EOF
[Unit]
Description=Vision V1 — Cloudflare tunnel
After=network-online.target vision-backend.service
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
ExecStart=$TUNNEL_EXECSTART
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vision-tunnel

[Install]
WantedBy=multi-user.target
EOF

# ---------------------------------------------------------------------------
# Enable and start
# ---------------------------------------------------------------------------
sudo systemctl daemon-reload
sudo systemctl enable vision-backend.service vision-tunnel.service

echo "Starting vision-backend..."
sudo systemctl restart vision-backend.service
sleep 4

echo "Starting vision-tunnel..."
sudo systemctl restart vision-tunnel.service
sleep 3

echo ""
echo "Done. Services are running and will auto-start on every boot."
echo ""
echo "Check status:"
echo "  sudo systemctl status vision-backend"
echo "  sudo systemctl status vision-tunnel"
echo ""
echo "Live logs:"
echo "  journalctl -u vision-backend -f"
echo "  journalctl -u vision-tunnel -f    # shows the public tunnel URL"
echo ""
echo "Useful commands:"
echo "  sudo systemctl restart vision-backend   # restart after git pull"
echo "  sudo systemctl stop vision-tunnel       # stop tunnel only"
