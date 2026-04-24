#!/usr/bin/env bash
# uninstall-service.sh — Remove the Capcan client systemd service and files.
# Run this on the target VM to fully uninstall.
#
# Usage: sudo ./uninstall-service.sh

set -euo pipefail

INSTALL_DIR="/opt/capcan-client"
SERVICE_NAME="capcan-client"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "==> Uninstalling Capcan client"

if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "    Stopping service..."
    systemctl stop "$SERVICE_NAME"
fi

if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "    Disabling service..."
    systemctl disable "$SERVICE_NAME"
fi

if [ -f "$UNIT_FILE" ]; then
    echo "    Removing unit file: ${UNIT_FILE}"
    rm -f "$UNIT_FILE"
    systemctl daemon-reload
    systemctl reset-failed "$SERVICE_NAME" 2>/dev/null || true
fi

if [ -d "$INSTALL_DIR" ]; then
    echo "    Removing install directory: ${INSTALL_DIR}"
    rm -rf "$INSTALL_DIR"
fi

echo "==> Capcan client uninstalled successfully."
