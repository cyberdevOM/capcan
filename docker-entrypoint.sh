#!/bin/bash
# docker-entrypoint.sh -- Capcan server container entrypoint.
#
# On first run (empty bundles volume):
#   - Seeds the pre-built client binary from the image into the mounted volume
#     so ensure_bundle() finds it immediately and only refreshes config.yaml.
#   - Generates and persists WEB_SECRET_KEY so Flask sessions survive restarts
#     without the operator needing to know or set the value.

set -e

BUNDLE_DIR=/app/dist/capcan-client-bundle
SEED_BINARY=/opt/capcan-seed/capcan-client
SECRET_KEY_FILE="$BUNDLE_DIR/.web_secret_key"

# -- Client binary ------------------------------------------------------------
if [ ! -f "$BUNDLE_DIR/capcan-client" ]; then
    echo "[ENTRYPOINT] Bundle volume is empty -- seeding pre-built client binary..."
    mkdir -p "$BUNDLE_DIR"
    cp "$SEED_BINARY" "$BUNDLE_DIR/capcan-client"
    chmod +x "$BUNDLE_DIR/capcan-client"
    echo "[ENTRYPOINT] Client binary seeded successfully."
else
    echo "[ENTRYPOINT] Client binary already present in volume -- skipping seed."
fi

# -- Web secret key -----------------------------------------------------------
# If WEB_SECRET_KEY has not been explicitly provided (or is still the placeholder
# value), generate one and persist it to the bundles volume. On subsequent runs
# the persisted key is loaded so existing user sessions remain valid.
if [ -z "$WEB_SECRET_KEY" ] || [ "$WEB_SECRET_KEY" = "changeme" ]; then
    mkdir -p "$BUNDLE_DIR"
    if [ -f "$SECRET_KEY_FILE" ]; then
        echo "[ENTRYPOINT] Loading persisted WEB_SECRET_KEY from volume."
        export WEB_SECRET_KEY
        WEB_SECRET_KEY=$(cat "$SECRET_KEY_FILE")
    else
        echo "[ENTRYPOINT] Generating new WEB_SECRET_KEY and persisting to volume..."
        export WEB_SECRET_KEY
        WEB_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        echo "$WEB_SECRET_KEY" > "$SECRET_KEY_FILE"
        chmod 600 "$SECRET_KEY_FILE"
        echo "[ENTRYPOINT] WEB_SECRET_KEY generated and saved."
    fi
else
    echo "[ENTRYPOINT] WEB_SECRET_KEY provided via environment -- using as-is."
fi

exec python -m src.server.web "$@"
