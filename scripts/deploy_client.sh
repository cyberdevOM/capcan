#!/usr/bin/env bash
# deploy_client.sh — Copy the Capcan client bundle to a remote Linux VM and optionally install it.
#
# Usage:
#   ./scripts/deploy_client.sh <user@host>             # copy only
#   ./scripts/deploy_client.sh <user@host> --install   # copy + install as systemd service
#   ./scripts/deploy_client.sh <user@host> --uninstall # stop and remove the systemd service
#
# Requirements on this machine: ssh + scp access to the VM (key-based auth recommended).
# The bundle must already be built via ./scripts/build_client.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE_DIR="$REPO_ROOT/dist/capcan-client-bundle"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <user@host> [--install|--uninstall]"
    exit 1
fi

TARGET="$1"
INSTALL="${2:-}"

if [ ! -d "$BUNDLE_DIR" ]; then
    echo "[!] Bundle not found at $BUNDLE_DIR"
    echo "    Run ./scripts/build_client.sh first."
    exit 1
fi

if [ "$INSTALL" = "--uninstall" ]; then
    echo "==> Uninstalling Capcan client on ${TARGET}"
    ssh -t "$TARGET" "sudo bash /tmp/capcan-client-bundle/uninstall-service.sh"
    echo "==> Done."
    exit 0
fi

echo "==> Deploying Capcan client bundle to ${TARGET}"

# Copy bundle to /tmp on target VM
scp -r "$BUNDLE_DIR" "${TARGET}:/tmp/capcan-client-bundle"

if [ "$INSTALL" = "--install" ]; then
    echo "==> Installing as systemd service on ${TARGET}"
    ssh -t "$TARGET" "sudo bash /tmp/capcan-client-bundle/install-service.sh"
else
    echo "==> Bundle copied to ${TARGET}:/tmp/capcan-client-bundle"
    echo ""
    echo "    To run manually on the VM:"
    echo "      ssh ${TARGET}"
    echo "      cd /tmp/capcan-client-bundle && ./capcan-client"
    echo ""
    echo "    To install as a service:"
    echo "      $0 ${TARGET} --install"
    echo ""
    echo "    To uninstall the service:"
    echo "      $0 ${TARGET} --uninstall"
fi

echo "==> Done."
