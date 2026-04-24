#!/usr/bin/env bash
# build_client.sh — Build the Capcan monitoring client binary.
#
# Usage:
#   ./scripts/build_client.sh [SERVER_IP] [SERVER_PORT]
#
# Outputs a self-contained deployable bundle at:
#   dist/capcan-client-bundle/
#     capcan-client          ← standalone binary (no Python needed on target)
#     config.yaml            ← pre-filled with SERVER_IP:SERVER_PORT, blank credentials
#     install-service.sh     ← optional: installs a systemd service on the target VM
#     uninstall-service.sh   ← optional: removes the systemd service and all installed files
#
# The binary is built for the current machine's architecture (x86_64 Linux).
# Run this script on a machine with the same arch as your target VMs.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVER_IP="${1:-$(hostname -I | awk '{print $1}')}"
SERVER_PORT="${2:-5000}"
BUNDLE_DIR="$REPO_ROOT/dist/capcan-client-bundle"

echo "==> Building Capcan client"
echo "    Server URL : http://${SERVER_IP}:${SERVER_PORT}"
echo "    Bundle dir : ${BUNDLE_DIR}"
echo ""

# Activate venv if present
if [ -f "$REPO_ROOT/venv/bin/activate" ]; then
    # shellcheck disable=SC1090
    source "$REPO_ROOT/venv/bin/activate"
fi

# Build the binary
cd "$REPO_ROOT"
pyinstaller --clean --noconfirm capcan-client.spec

# Create the deployment bundle directory
mkdir -p "$BUNDLE_DIR"
cp dist/capcan-client "$BUNDLE_DIR/capcan-client"

# Write a fresh config.yaml with the correct server URL and blank credentials
cat > "$BUNDLE_DIR/config.yaml" <<YAML
server_url: http://${SERVER_IP}:${SERVER_PORT}
platform: linux
client_id: ''
secret_key: ''
YAML

# Write default settings.yaml (remotely configurable via Capcan dashboard)
cat > "$BUNDLE_DIR/settings.yaml" <<YAML
# Remotely configurable settings — these can be updated from the Capcan web UI.
# Changes pushed from the dashboard take effect on the next telemetry cycle.
interval: 300
collect:
  cpu: true
  memory: true
  disk: true
  network: true
  processes: true
YAML

# Write the service installer script (runs on the target VM)
cat > "$BUNDLE_DIR/install-service.sh" <<'SERVICE'
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
cp "$(dirname "$0")/capcan-client" "$INSTALL_DIR/"
cp "$(dirname "$0")/config.yaml"   "$INSTALL_DIR/"
cp "$(dirname "$0")/settings.yaml" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/capcan-client"

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
SERVICE

chmod +x "$BUNDLE_DIR/install-service.sh"

# Write the service uninstaller script (runs on the target VM)
cat > "$BUNDLE_DIR/uninstall-service.sh" <<'UNINSTALL'
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
UNINSTALL

chmod +x "$BUNDLE_DIR/uninstall-service.sh"
chmod +x "$BUNDLE_DIR/capcan-client"

echo ""
echo "==> Build complete!"
echo ""
echo "    Bundle: ${BUNDLE_DIR}/"
echo "    $(ls -lh "$BUNDLE_DIR/capcan-client" | awk '{print $5, $9}')"
echo ""
echo "    Deploy to a VM:"
echo "      ./scripts/deploy_client.sh <user@vm-ip>"
