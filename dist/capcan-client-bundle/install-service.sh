#!/usr/bin/env bash
# install-service.sh — Install Capcan client as a systemd service.
# Run this on the target VM after copying the bundle.
#
# Usage: sudo ./install-service.sh

set -euo pipefail

INSTALL_DIR="/opt/capcan-client"
SERVICE_NAME="capcan-client"

echo "==> Installing Capcan client to ${INSTALL_DIR}"
mkdir -p "$INSTALL_DIR"
cp "$(dirname "$0")/capcan-client"          "$INSTALL_DIR/"
cp "$(dirname "$0")/config.yaml"            "$INSTALL_DIR/"
cp "$(dirname "$0")/settings.yaml"          "$INSTALL_DIR/"
cp "$(dirname "$0")/uninstall-service.sh"   "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/capcan-client"
chmod +x "$INSTALL_DIR/uninstall-service.sh"

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<UNIT
[Unit]
Description=Capcan Monitoring Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/capcan-client
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start  "$SERVICE_NAME"
echo "==> Service started. Status:"
systemctl status "$SERVICE_NAME" --no-pager
