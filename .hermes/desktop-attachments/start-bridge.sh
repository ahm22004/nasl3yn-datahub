#!/bin/bash
# Auto-start bridge + cloudflared tunnel for Binance API
# systemd services handle this now:
#   sudo systemctl enable --now binance-bridge.service
#   sudo systemctl enable --now cloudflared-tunnel.service
# This script is for manual restart if needed.

set -e

cd "$(dirname "$0")/.."

echo "moaz1234" | sudo -S systemctl restart binance-bridge.service 2>/dev/null
sleep 2
echo "moaz1234" | sudo -S systemctl restart cloudflared-tunnel.service 2>/dev/null
echo "Services restarted"
echo "Bridge URL: https://bridge.nasl3yn.com"
