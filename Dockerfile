# ── Stage 1: Build the client binary ─────────────────────────────────────────
# Uses a full builder image to compile the client with PyInstaller.
# None of the build tools enter the final runtime image.
FROM python:3.11-slim AS builder

WORKDIR /build

# gcc + binutils are required by PyInstaller to produce a self-contained ELF binary.
# libpq-dev satisfies psycopg2-binary's build-time header requirement.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        binutils \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install only the packages the client itself imports (+ PyInstaller).
# These are intentionally separate from the server's requirements.txt to keep
# the builder layer small and independent.
RUN pip install --no-cache-dir \
        pyinstaller==6.19.0 \
        psutil \
        pyyaml \
        requests \
        cryptography

COPY . .

# Build the binary with a placeholder IP.
# The real SERVER_IP is stamped into config.yaml at container startup by
# ensure_bundle() — so the IP baked here never reaches a deployed client.
RUN bash scripts/build_client.sh 0.0.0.0 5000


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
# Lean production image — only server deps, source code, and the pre-built binary.
FROM python:3.11-slim AS runtime

WORKDIR /app

# libpq-dev is needed at runtime by psycopg2-binary.
# gcc is needed by paramiko's optional C extension (harmless if absent, but avoids warnings).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Install server dependencies.
# The editable git+ssh line in requirements.txt cannot run inside Docker (no SSH keys),
# so we skip it. The package itself is installed non-editable from the local source.
# pyinstaller is a build tool only needed in the builder stage — excluded here too.
COPY . .

RUN pip install --no-cache-dir . && \
    grep -v "^-e git\|^pyinstaller" requirements.txt | pip install --no-cache-dir -r /dev/stdin

# Copy the pre-built client binary to a seed location that is NOT the volume mount
# path. The entrypoint copies it into the volume on first run, so ensure_bundle()
# sees an existing binary and only refreshes config.yaml rather than rebuilding.
COPY --from=builder /build/dist/capcan-client-bundle/capcan-client \
                    /opt/capcan-seed/capcan-client

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/docker-entrypoint.sh"]
