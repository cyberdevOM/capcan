#!/usr/bin/env bash
# build_client.sh — Build the Capcan monitoring client binary.
#
# Usage:
#   ./scripts/build_client.sh [SERVER_IP] [SERVER_PORT] [--demo]
#
# Outputs a self-contained deployable bundle at:
#   dist/capcan-client-bundle/
#     capcan-client          ← standalone binary (no Python needed on target)
#     config.yaml            ← pre-filled with SERVER_IP:SERVER_PORT, blank credentials
#     settings.yaml          ← configurable: interval, collect, watchers toggles
#     install-service.sh     ← optional: installs a systemd service on the target VM
#     uninstall-service.sh   ← optional: removes the systemd service and all installed files
#
# When --demo is passed:
#   demo_attack_sim.py is included in the bundle and demo_mode is set to true
#   in settings.yaml. Run it on the target to generate realistic attack traffic.
#
# The binary is built for the current machine's architecture (x86_64 Linux).
# Run this script on a machine with the same arch as your target VMs.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVER_IP="${1:-$(hostname -I | awk '{print $1}')}"
SERVER_PORT="${2:-5000}"
BUNDLE_DIR="$REPO_ROOT/dist/capcan-client-bundle"

# Parse optional --demo flag from any position
DEMO_MODE=false
for arg in "$@"; do
    if [ "$arg" = "--demo" ]; then
        DEMO_MODE=true
    fi
done

echo "==> Building Capcan client"
echo "    Server URL : http://${SERVER_IP}:${SERVER_PORT}"
echo "    Bundle dir : ${BUNDLE_DIR}"
echo "    Demo mode  : ${DEMO_MODE}"
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

# Write settings.yaml — includes all toggles; demo_mode driven by --demo flag
# Keep in sync with client_main.py and deployer.py
cat > "$BUNDLE_DIR/settings.yaml" <<YAML
# Remotely configurable settings — can be updated from the Capcan web UI.
# Changes pushed from the dashboard take effect on the next telemetry cycle.
interval: 180
demo_mode: ${DEMO_MODE}
collect:
  cpu: true
  memory: true
  disk: true
  network: true
  processes: true
  temperatures: true
  top_processes: true
watchers:
  file_integrity: true
  process: true
  network: true
  login: true
  service: true
dynamic_collectors: []
YAML

# Include the demo attack simulator when building a demo bundle.
# The C source is compiled to a standalone binary so no Python is needed.
if [ "$DEMO_MODE" = "true" ]; then
    echo "    [demo] Compiling demo_attack_sim.c …"
    gcc -O2 -Wall -o "$BUNDLE_DIR/demo_attack_sim" \
        "$REPO_ROOT/src/client_template/demo_attack_sim.c" -lpthread
    echo "    [demo] demo_attack_sim binary included in bundle"
    echo "    [demo] Run on target: ./demo_attack_sim --all"
    echo ""
fi

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
cp "$(dirname "$0")/capcan-client"          "$INSTALL_DIR/"
cp "$(dirname "$0")/config.yaml"            "$INSTALL_DIR/"
cp "$(dirname "$0")/settings.yaml"          "$INSTALL_DIR/"
cp "$(dirname "$0")/uninstall-service.sh"   "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/capcan-client"
chmod +x "$INSTALL_DIR/uninstall-service.sh"
if [ -f "$(dirname "$0")/demo_attack_sim" ]; then
    cp "$(dirname "$0")/demo_attack_sim" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/demo_attack_sim"
fi

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

echo "==> Cleaning up staging directory"
rm -rf /tmp/capcan-client-bundle
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
