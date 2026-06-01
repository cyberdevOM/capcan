"""
Capcan Monitoring Client

Collects system telemetry (CPU, memory, disk, network, processes) and sends
it to the Capcan server at a configurable interval. Telemetry submissions also
serve as the liveness signal — no separate heartbeat.

Config files (both live next to the executable):
  config.yaml   — fixed: server_url, client_id, secret_key. Never changed remotely.
  settings.yaml — changeable: interval, collect toggles. Updated via Capcan dashboard.

Flow:
  1. Load config.yaml + settings.yaml
  2. If not yet registered, POST to /api/v1/clients/register and save credentials
  3. Loop: collect metrics → sign with HMAC → POST to /api/v1/telemetry/
           → apply any settings pushed from dashboard → sleep
"""

import copy
import datetime as dt
import hashlib
import hmac
import json
import logging
import math
import os
import platform
import random
import re
import socket
import subprocess
import sys
import threading
import time
from typing import Optional

import psutil
import requests
import yaml

# When frozen by PyInstaller, __file__ points into the temp extraction dir.
# Both config files must live *next to* the executable so each deployment can
# have its own credentials and independently managed settings.
if getattr(sys, "frozen", False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(base_dir, "config.yaml")
SETTINGS_PATH = os.path.join(base_dir, "settings.yaml")
CLIENT_VERSION = 0.1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("capcan-client")

DEFAULT_SETTINGS = { # Keep in sync with scripts/build_client.sh and deployer.py
    "interval": 120,
    "demo_mode": "false",
    "demo_alerts_per_hour": 20,
    "collect": {
        "cpu": True,
        "memory": True,
        "disk": True,
        "network": True,
        "processes": True,
        "temperatures": True,
        "top_processes": True,
    },
    "watchers": {
        "file_integrity": True,
        "process": True,
        "network": True,
        "login": True,
        "service": True,
    },
    "dynamic_collectors": [],
}


# Config helpers

def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def load_settings() -> dict:
    """Load changeable settings. Falls back to defaults if file is missing or corrupt."""
    try:
        with open(SETTINGS_PATH) as f:
            on_disk = yaml.safe_load(f) or {}
        # Deep-merge with defaults so new keys are always present
        merged = dict(DEFAULT_SETTINGS)
        merged["collect"] = dict(DEFAULT_SETTINGS["collect"])
        merged["watchers"] = dict(DEFAULT_SETTINGS["watchers"])
        if isinstance(on_disk.get("interval"), (int, float)):
            merged["interval"] = int(on_disk["interval"])
        dm = on_disk.get("demo_mode")
        if dm in ("false", "simulated", "script"):
            merged["demo_mode"] = dm
        elif isinstance(dm, bool):  # migrate old boolean format
            merged["demo_mode"] = "simulated" if dm else "false"
        if isinstance(on_disk.get("demo_alerts_per_hour"), (int, float)):
            merged["demo_alerts_per_hour"] = int(on_disk["demo_alerts_per_hour"])
        if isinstance(on_disk.get("collect"), dict):
            for k in merged["collect"]:
                if isinstance(on_disk["collect"].get(k), bool):
                    merged["collect"][k] = on_disk["collect"][k]
        if isinstance(on_disk.get("watchers"), dict):
            for k in merged["watchers"]:
                if isinstance(on_disk["watchers"].get(k), bool):
                    merged["watchers"][k] = on_disk["watchers"][k]
        if isinstance(on_disk.get("dynamic_collectors"), list):
            merged["dynamic_collectors"] = on_disk["dynamic_collectors"]
        return merged
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    with open(SETTINGS_PATH, "w") as f:
        yaml.dump(settings, f, default_flow_style=False, sort_keys=False)


def apply_remote_settings(current: dict, incoming: dict) -> tuple[dict, bool]:
    """
    Merge server-pushed settings into current settings.
    Returns (updated_settings, changed) where changed indicates a save is needed.
    Forbidden keys (server_url, client_id, secret_key) are silently ignored.
    """
    updated = dict(current)
    updated["collect"] = dict(current.get("collect", DEFAULT_SETTINGS["collect"]))
    updated["watchers"] = dict(current.get("watchers", DEFAULT_SETTINGS["watchers"]))
    changed = False

    if "interval" in incoming and isinstance(incoming["interval"], (int, float)):
        new_interval = int(incoming["interval"])
        if new_interval != updated.get("interval"):
            updated["interval"] = new_interval
            changed = True

    if "demo_mode" in incoming:
        dm = incoming["demo_mode"]
        if dm in ("false", "simulated", "script"):
            # New string format (rebuilt clients)
            if dm != updated.get("demo_mode"):
                updated["demo_mode"] = dm
                changed = True
        elif isinstance(dm, bool):
            # Old bool format — migrate to string
            new_dm = "simulated" if dm else "false"
            if new_dm != updated.get("demo_mode"):
                updated["demo_mode"] = new_dm
                changed = True

    # Also accept old demo_sim_mode field (pushed for backward compat with old binaries)
    if "demo_sim_mode" in incoming and isinstance(incoming["demo_sim_mode"], str):
        _legacy_map = {'off': 'false', 'synthetic': 'simulated', 'script': 'script'}
        new_dm = _legacy_map.get(incoming["demo_sim_mode"])
        if new_dm and new_dm != updated.get("demo_mode"):
            updated["demo_mode"] = new_dm
            changed = True

    if "demo_alerts_per_hour" in incoming and isinstance(incoming["demo_alerts_per_hour"], (int, float)):
        new_rate = int(incoming["demo_alerts_per_hour"])
        if new_rate != updated.get("demo_alerts_per_hour"):
            updated["demo_alerts_per_hour"] = new_rate
            changed = True

    if "collect" in incoming and isinstance(incoming["collect"], dict):
        for key in DEFAULT_SETTINGS["collect"]:
            if key in incoming["collect"] and isinstance(incoming["collect"][key], bool):
                if incoming["collect"][key] != updated["collect"].get(key):
                    updated["collect"][key] = incoming["collect"][key]
                    changed = True

    if "watchers" in incoming and isinstance(incoming["watchers"], dict):
        for key in DEFAULT_SETTINGS["watchers"]:
            if key in incoming["watchers"] and isinstance(incoming["watchers"][key], bool):
                if incoming["watchers"][key] != updated["watchers"].get(key):
                    updated["watchers"][key] = incoming["watchers"][key]
                    changed = True

    if "dynamic_collectors" in incoming and isinstance(incoming["dynamic_collectors"], list):
        if incoming["dynamic_collectors"] != updated.get("dynamic_collectors"):
            updated["dynamic_collectors"] = incoming["dynamic_collectors"]
            changed = True

    return updated, changed


def detect_platform() -> str:
    """Map sys.platform to a value the server accepts: linux / windows / macos."""
    s = sys.platform.lower()
    if s.startswith("linux"):
        return "linux"
    if s.startswith("win"):
        return "windows"
    if s == "darwin":
        return "macos"
    return "linux"


def register(config: dict) -> dict:
    """
    Register this client with the server.
    Returns an updated config dict with client_id and secret_key populated.
    Raises on failure so the caller can decide whether to abort or retry.
    """
    url = config["server_url"].rstrip("/") + "/api/v1/clients/register"
    payload = {
        "hostname": socket.gethostname(),
        "platform": detect_platform(),
        "version": CLIENT_VERSION,
    }
    log.info("Registering with server at %s …", url)
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    config["client_id"] = data["client_id"]
    config["secret_key"] = data["secret_key"]
    save_config(config)
    log.info("Registered successfully. client_id=%s", config["client_id"])
    return config

def _iso_timestamp() -> str:
    """Return current UTC time in the exact format the server expects: YYYY-MM-DDTHH:MM:SSZ"""
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sign_request(client_id: str, secret_key: str, body_bytes: bytes) -> dict:
    """
    Build signed request headers.

    HMAC message = client_id + timestamp (UTF-8) || body bytes
    Signature format: sha256=<hexdigest>
    """
    timestamp = _iso_timestamp()
    message = client_id.encode("utf-8") + timestamp.encode("utf-8") + body_bytes
    digest = hmac.new(
        key=secret_key.encode("utf-8"),
        msg=message,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return {
        "X-Client-ID": client_id,
        "X-Timestamp": timestamp,
        "X-Signature": f"sha256={digest}",
        "Content-Type": "application/json",
    }

# Metric collection

# Counters from the previous collection cycle.
# Seeded at import time so the first collection has a real delta (service-start → first interval).
try:
    prev_disk_io: Optional[object] = psutil.disk_io_counters()
    prev_net_io: Optional[object] = psutil.net_io_counters()
except Exception:
    prev_disk_io = None
    prev_net_io = None

# Warm up cpu_percent — first call always returns 0.0, second is accurate.
psutil.cpu_percent(interval=None)

# Per-process random offset so demo outlier timing differs between client instances.
DEMO_SEED_OFFSET: int = random.randint(0, 0xFFFF)

# Alert scenarios for demo mode — covers all 4 severities and a spread of event types.
DEMO_ALERT_SCENARIOS = [
    {
        "severity": "critical",
        "event_type": "file_modified",
        "details": {
            "file_path": "/etc/passwd",
            "process_name": "python3",
            "process_id": 4821,
            "description": "Sensitive system file modified by unexpected process",
        },
    },
    {
        "severity": "critical",
        "event_type": "process_started",
        "details": {
            "process_name": "nc",
            "process_id": 9342,
            "command_line": "nc -lvp 4444 -e /bin/bash",
            "description": "Reverse shell listener detected",
        },
    },
    {
        "severity": "critical",
        "event_type": "login_failed",
        "details": {
            "description": "SSH brute-force: 87 failed attempts in 60 seconds",
            "attempt_count": 87,
            "source_ip": "185.220.101.47",
        },
    },
    {
        "severity": "high",
        "event_type": "network_connection",
        "details": {
            "description": "Outbound connection to known C2 IP range",
            "destination_ip": "10.0.99.254",
            "destination_port": 4443,
            "protocol": "TCP",
        },
    },
    {
        "severity": "high",
        "event_type": "file_created",
        "details": {
            "file_path": "/tmp/.hidden_script.sh",
            "process_name": "bash",
            "process_id": 7102,
            "description": "Hidden executable script created in /tmp",
        },
    },
    {
        "severity": "high",
        "event_type": "service_stopped",
        "details": {
            "service_name": "ufw",
            "description": "Firewall service stopped unexpectedly",
        },
    },
    {
        "severity": "medium",
        "event_type": "process_terminated",
        "details": {
            "process_name": "auditd",
            "process_id": 512,
            "description": "Audit logging daemon was killed",
        },
    },
    {
        "severity": "medium",
        "event_type": "file_deleted",
        "details": {
            "file_path": "/var/log/auth.log",
            "process_name": "rm",
            "process_id": 3317,
            "description": "Authentication log file deleted",
        },
    },
    {
        "severity": "medium",
        "event_type": "custom",
        "details": {
            "description": "CPU saturation sustained for 2+ minutes — possible load-based attack",
            "cpu_percent": 97.8,
            "sustained_seconds": 135,
        },
    },
    {
        "severity": "info",
        "event_type": "login_success",
        "details": {
            "username": "admin",
            "source_ip": "192.168.1.22",
            "description": "Root login via SSH outside business hours",
        },
    },
    {
        "severity": "info",
        "event_type": "file_modified",
        "details": {
            "file_path": "/etc/crontab",
            "process_name": "crontab",
            "process_id": 2201,
            "description": "Crontab modified — new scheduled task added",
        },
    },
]

# Target alert submission rate in demo mode.
DEMO_ALERTS_PER_HOUR = 20


def collect_demo_metrics(settings: dict) -> dict:
    """
    Generate synthetic telemetry for demo mode.

    Normal values follow a slow sine wave. Approximately 15% of 30-second
    windows include a single-metric spike that reaches alert-worthy levels.
    The spike type is stable within the window (same bucket seed) but varies
    across windows and differs between client processes (DEMO_SEED_OFFSET).
    """
    collect = settings.get("collect", DEFAULT_SETTINGS["collect"])
    t = time.time()
    wave = math.sin(t / 60) * 0.5 + 0.5  # 0–1, slow oscillation

    # Decide spike type for this 30-second window.
    bucket_rng = random.Random(int(t // 30) ^ DEMO_SEED_OFFSET)
    enabled = [k for k, v in collect.items() if v]
    spike_pool = enabled + ["load_average"]  # load_average always present
    outlier = bucket_rng.choice(spike_pool) if bucket_rng.random() < 0.15 else None

    metrics: dict = {}

    if collect.get("cpu", True):
        if outlier == "cpu":
            metrics["cpu_percent"] = round(bucket_rng.uniform(91, 99.5), 2)
        else:
            metrics["cpu_percent"] = round(20 + wave * 55 + random.uniform(-3, 3), 2)

    if collect.get("memory", True):
        if outlier == "memory":
            mem_pct = round(bucket_rng.uniform(89, 97), 2)
        else:
            mem_pct = round(45 + wave * 30 + random.uniform(-2, 2), 2)
        metrics["memory_percent"] = mem_pct
        metrics["memory_available"] = int(4096 * (1 - mem_pct / 100))

    if collect.get("disk", True):
        if outlier == "disk":
            metrics["disk_usage"] = round(bucket_rng.uniform(92, 99), 2)
            metrics["disk_read_bytes"] = random.randint(50_000_000, 200_000_000)
            metrics["disk_write_bytes"] = random.randint(20_000_000, 100_000_000)
        else:
            metrics["disk_usage"] = round(55 + wave * 10 + random.uniform(-1, 1), 2)
            metrics["disk_read_bytes"] = random.randint(0, 5_000_000)
            metrics["disk_write_bytes"] = random.randint(0, 2_000_000)

    if collect.get("network", True):
        if outlier == "network":
            metrics["network_sent_bytes"] = random.randint(50_000_000, 300_000_000)
            metrics["network_recv_bytes"] = random.randint(100_000_000, 500_000_000)
        else:
            metrics["network_sent_bytes"] = random.randint(10_000, 500_000)
            metrics["network_recv_bytes"] = random.randint(50_000, 2_000_000)

    if collect.get("processes", True):
        if outlier == "processes":
            metrics["process_count"] = random.randint(450, 600)
        else:
            metrics["process_count"] = random.randint(120, 180)

    if outlier == "load_average":
        spike = bucket_rng.uniform(8, 16)
        metrics["load_average"] = [
            round(spike + random.uniform(0, 0.5), 2),
            round(spike * 0.85 + random.uniform(0, 0.3), 2),
            round(spike * 0.70 + random.uniform(0, 0.2), 2),
        ]
    else:
        metrics["load_average"] = [
            round(0.5 + wave * 2 + random.uniform(0, 0.3), 2),
            round(0.4 + wave * 1.8 + random.uniform(0, 0.2), 2),
            round(0.3 + wave * 1.5 + random.uniform(0, 0.1), 2),
        ]

    metrics["uptime_seconds"] = int(t % 86400) + 3600
    metrics["platform"] = detect_platform()
    metrics["hostname"] = socket.gethostname()
    return metrics

def collect_metrics(settings: dict, watchdog: Optional["WatchdogCollector"] = None) -> dict:
    """Collect a telemetry snapshot, respecting enabled/disabled collect flags."""
    if settings.get("demo_mode") == "simulated":
        return collect_demo_metrics(settings)

    global prev_disk_io, prev_net_io

    collect = settings.get("collect", DEFAULT_SETTINGS["collect"])
    metrics: dict = {}

    if collect.get("cpu", True):
        metrics["cpu_percent"] = round(psutil.cpu_percent(interval=1), 2)

    if collect.get("memory", True):
        mem = psutil.virtual_memory()
        metrics["memory_percent"] = round(mem.percent, 2)
        metrics["memory_available"] = mem.available // (1024 * 1024)  # MB

    if collect.get("disk", True):
        root = "C:\\" if sys.platform.startswith("win") else "/"
        disk = psutil.disk_usage(root)
        metrics["disk_usage"] = round(disk.percent, 2)

        # Delta counters: subtract the previous cycle's reading so we report
        # bytes-per-interval rather than a monotonically growing total.
        curr_disk = psutil.disk_io_counters()
        if curr_disk and prev_disk_io:
            metrics["disk_read_bytes"] = max(0, curr_disk.read_bytes - prev_disk_io.read_bytes)
            metrics["disk_write_bytes"] = max(0, curr_disk.write_bytes - prev_disk_io.write_bytes)
        prev_disk_io = curr_disk
    else:
        prev_disk_io = None  # reset so re-enabling the collector doesn't produce a spike

    if collect.get("network", True):
        curr_net = psutil.net_io_counters()
        if curr_net and prev_net_io:
            metrics["network_sent_bytes"] = max(0, curr_net.bytes_sent - prev_net_io.bytes_sent)
            metrics["network_recv_bytes"] = max(0, curr_net.bytes_recv - prev_net_io.bytes_recv)
        prev_net_io = curr_net
    else:
        prev_net_io = None  # reset so re-enabling the collector doesn't produce a spike

    if collect.get("processes", True):
        metrics["process_count"] = len(psutil.pids())

    if hasattr(os, "getloadavg"):
        la = os.getloadavg()
        metrics["load_average"] = [round(x, 2) for x in la]

    metrics["uptime_seconds"] = int(time.time() - psutil.boot_time())
    metrics["platform"] = detect_platform()
    metrics["hostname"] = socket.gethostname()

    # Extended collectors — enrich the payload with additional real-world metrics.
    # Each function mutates `metrics` in-place and returns nothing.
    collect_cpu_extended(settings, metrics)
    collect_memory_extended(settings, metrics)
    collect_top_processes(settings, metrics)
    collect_temperatures(settings, metrics)

    # DynamicCollector is instantiated fresh each cycle so any spec changes
    # pushed from the dashboard are picked up without restarting the client.
    DynamicCollector(settings).collect(metrics)

    # Watchdog health fields — appended last so they ride with every payload
    if watchdog is not None:
        watchdog.collect(metrics)

    return metrics

def send_telemetry(config: dict, metrics: dict) -> dict:
    """
    Sign and POST telemetry data to the server.
    Returns the parsed JSON response on success.
    Raises requests.HTTPError on HTTP error responses.
    """
    return _signed_post(config, "/api/v1/telemetry/", metrics)


def send_alert(config: dict, alert_data: dict) -> dict:
    """
    Sign and POST a single alert to the server.
    Uses the same HMAC scheme as send_telemetry.
    Raises requests.HTTPError on HTTP error responses.
    """
    return _signed_post(config, "/api/v1/alerts/", alert_data)


def _signed_post(config: dict, path: str, payload: dict) -> dict:
    """
    Internal helper: JSON-encode *payload*, sign it with HMAC, POST it.
    Both send_telemetry and send_alert use this so the signing logic stays
    in one place.
    """
    url = config["server_url"].rstrip("/") + path
    body_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = sign_request(config["client_id"], config["secret_key"], body_bytes)
    resp = requests.post(url, data=body_bytes, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def send_demo_alert(config: dict, settings: dict, interval: int) -> None:
    """
    Randomly submit a demo alert, targeting demo_alerts_per_hour over time.
    Alert failures are logged but never propagate — they must not crash the main loop.
    """
    rate = settings.get("demo_alerts_per_hour", DEMO_ALERTS_PER_HOUR)
    per_cycle_prob = min(0.90, rate * interval / 3600)
    if random.random() >= per_cycle_prob:
        return

    scenario = copy.deepcopy(random.choice(DEMO_ALERT_SCENARIOS))
    try:
        result = send_alert(config, scenario)
        log.info(
            "Demo alert submitted: severity=%s event=%s alert_id=%s",
            scenario["severity"],
            scenario["event_type"],
            result.get("alert_id"),
        )
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        log.warning("Demo alert rejected (HTTP %s): %s", status, exc)
    except Exception as exc:
        log.warning("Demo alert submission error: %s", exc)


# Honeypot
# Canary files: each entry has platform-specific paths and realistic-looking content.
HONEYPOT_FILES = [
    {
        "path_unix": "~/.capcan/.env",
        "path_windows": os.path.join(
            os.environ.get("APPDATA", "C:\\ProgramData"), "capcan", ".env"
        ),
        "content": (
            "# Capcan production service credentials\n"
            "DATABASE_URL=postgres://capcan:Xy9mP3@db.internal:5432/capcan_prod\n"
            "SECRET_KEY=capcan-prod-sk-7f3a9b2c1d4e5f6a\n"
            "API_TOKEN=tok_prod_8f2a1b3c4d5e6f7a8b9c\n"
            "ADMIN_PASSWORD=C@pcan-Adm1n-2024!\n"
        ),
        "description": "production environment credentials",
    },
    {
        "path_unix": "~/.ssh/capcan_id_rsa",
        "path_windows": os.path.join(
            os.environ.get("USERPROFILE", os.path.expanduser("~")), ".ssh", "loc_id_rsa"
        ),
        "content": (
            "-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "b3BlbnNzaC1rZXktdjEAAAAA[CAPCAN-CANARY-8f2a1b3c4d5e6f7a]\n"
            "-----END OPENSSH PRIVATE KEY-----\n"
        ),
        "description": "SSH private key",
    },
    {
        "path_unix": "/tmp/.capcan_session",
        "path_windows": os.path.join(
            os.environ.get("TEMP", "C:\\Windows\\Temp"), ".capcan_session"
        ),
        "content": (
            "session_id=capcan_prod_sess_8f2a1b3c4d5e6f7a\n"
            "token=Bearer eyJhbGciOiJIUzI1NiJ9.cap.can\n"
            "expires=9999-12-31T23:59:59Z\n"
            "user=wheelbarrow\n"
        ),
        "description": "active session token",
    },
]

def get_honeypot_path(hpf: dict) -> str:
    if sys.platform.startswith("win"):
        return hpf["path_windows"]
    return os.path.expanduser(hpf["path_unix"])

def deploy_honeypot_files() -> list:
    """Write canary files to disk. Returns a list of successfully deployed paths."""
    deployed = []
    for hpf in HONEYPOT_FILES:
        path = get_honeypot_path(hpf)
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            if not os.path.exists(path):
                with open(path, "w") as fh:
                    fh.write(hpf["content"])
            deployed.append(path)
        except OSError as exc:
            log.warning("Honeypot: could not deploy %s: %s", path, exc)
    return deployed

def send_honeypot_alert(config: dict, path: str, access_type: str) -> None:
    """Fire a critical alert for honeypot file access. Never raises."""
    hpf = next((h for h in HONEYPOT_FILES if get_honeypot_path(h) == path), None)
    description = hpf["description"] if hpf else os.path.basename(path)
    alert = {
        "severity": "critical",
        "event_type": "honeypot_access",
        "details": {
            "file_path": path,
            "access_type": access_type,
            "description": f"Honeypot {access_type} detected on {description}",
        },
    }
    try:
        result = send_alert(config, alert)
        log.warning(
            "HONEYPOT ALERT fired: %s %s — alert_id=%s",
            access_type,
            path,
            result.get("alert_id"),
        )
    except Exception as exc:
        log.error("Honeypot: failed to send alert for %s: %s", path, exc)

def poll_atime(watched_paths: list, config: dict, interval: int = 30) -> None:
    """
    Background thread: detect honeypot file reads via atime changes.
    Works on Linux/macOS where filesystem atime updates are enabled (default).
    Silently skips paths that are inaccessible.
    """
    last_atimes: dict = {}
    for path in watched_paths:
        try:
            last_atimes[path] = os.stat(path).st_atime
        except OSError:
            last_atimes[path] = 0.0

    while True:
        time.sleep(interval)
        for path in watched_paths:
            try:
                current_atime = os.stat(path).st_atime
            except OSError:
                continue
            # Require >1 s change to avoid false positives from OS metadata updates.
            if current_atime > last_atimes.get(path, 0.0) + 1.0:
                last_atimes[path] = current_atime
                send_honeypot_alert(config, path, "read")

def start_honeypot_watcher(config: dict) -> None:
    """
    Deploy canary files then start watchdog + atime-poll threads.
    Both threads are daemon threads — they terminate with the main process.
    Logs a warning and returns silently if watchdog is not installed.
    """
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        log.warning("Honeypot: watchdog not installed — file-system monitoring disabled")
        return

    deployed = deploy_honeypot_files()
    if not deployed:
        log.warning("Honeypot: no canary files could be deployed — watcher not started")
        return

    log.info("Honeypot: %d canary file(s) deployed", len(deployed))
    watched_set = set(deployed)

    class HoneypotHandler(FileSystemEventHandler):
        def _fire(self, access_type: str, src_path: str) -> None:
            if src_path in watched_set:
                send_honeypot_alert(config, src_path, access_type)

        def on_modified(self, event):
            if not event.is_directory:
                self._fire("modified", event.src_path)

        def on_deleted(self, event):
            if not event.is_directory:
                self._fire("deleted", event.src_path)

        def on_moved(self, event):
            if not event.is_directory:
                self._fire("moved", event.src_path)

        def on_created(self, event):
            # Catches recreation after deletion
            if not event.is_directory:
                self._fire("created", event.src_path)

    handler = HoneypotHandler()
    observer = Observer()
    for directory in {os.path.dirname(p) for p in deployed if os.path.dirname(p)}:
        observer.schedule(handler, directory, recursive=False)
    observer.daemon = True
    observer.start()

    atime_thread = threading.Thread(
        target=poll_atime,
        args=(list(deployed), config),
        daemon=True,
        name="honeypot-atime",
    )
    atime_thread.start()

    log.info("Honeypot: watcher active on %d director(ies)", len({os.path.dirname(p) for p in deployed}))



# Extended collectors
def collect_cpu_extended(settings: dict, metrics: dict) -> None:
    """Extend metrics with per-core CPU usage and clock frequency."""
    if not settings.get("collect", {}).get("cpu", True):
        return
    try:
        per_core = psutil.cpu_percent(percpu=True, interval=None)
        metrics["cpu_core_count"] = len(per_core)
        metrics["cpu_core_usage"] = per_core
    except Exception as exc:
        log.debug("collect_cpu_extended (per-core): %s", exc)
    try:
        freq = psutil.cpu_freq()
        if freq:
            metrics["cpu_freq_mhz"] = round(freq.current, 1)
    except Exception:
        pass

def collect_memory_extended(settings: dict, metrics: dict) -> None:
    """Extend metrics with swap memory statistics."""
    if not settings.get("collect", {}).get("memory", True):
        return
    try:
        swap = psutil.swap_memory()
        metrics["swap_percent"] = round(swap.percent, 2)
        metrics["swap_used_mb"] = swap.used // (1024 * 1024)
        metrics["swap_total_mb"] = swap.total // (1024 * 1024)
    except Exception as exc:
        log.debug("collect_memory_extended: %s", exc)

def collect_top_processes(settings: dict, metrics: dict, top_n: int = 5) -> None:
    """Extend metrics with the top N processes by CPU and memory usage."""
    if not settings.get("collect", {}).get("top_processes", True):
        return
    try:
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        top_cpu = sorted(procs, key=lambda p: p.get("cpu_percent") or 0.0, reverse=True)[:top_n]
        metrics["top_cpu_processes"] = [
            {
                "pid": p["pid"],
                "name": p["name"],
                "cpu_percent": round(p.get("cpu_percent") or 0.0, 2),
            }
            for p in top_cpu
        ]
        top_mem = sorted(procs, key=lambda p: p.get("memory_percent") or 0.0, reverse=True)[:top_n]
        metrics["top_memory_processes"] = [
            {
                "pid": p["pid"],
                "name": p["name"],
                "memory_percent": round(p.get("memory_percent") or 0.0, 2),
            }
            for p in top_mem
        ]
    except Exception as exc:
        log.debug("collect_top_processes: %s", exc)

def collect_temperatures(settings: dict, metrics: dict) -> None:
    """Extend metrics with CPU temperature sensor readings (Linux / macOS only)."""
    if not settings.get("collect", {}).get("temperatures", True):
        return
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return
        readings = []
        for sensor_name, entries in temps.items():
            for entry in entries:
                if entry.current is not None:
                    readings.append({
                        "sensor": sensor_name,
                        "label": entry.label or sensor_name,
                        "celsius": round(entry.current, 1),
                    })
        if readings:
            metrics["temperatures"] = readings
    except Exception:
        pass  # sensors_temperatures() absent on some platforms / Windows


# Dynamic collector  —  example: runtime-configurable metric collection
class DynamicCollector:
    """
    Runtime-configurable metric collector driven by specs in settings.

    A dynamic collector executes collection logic defined in remote settings
    rather than hard-coded in the client. This allows new metrics to be pushed
    from the Capcan dashboard without requiring a client update or redeployment.

    Each spec in settings['dynamic_collectors'] is a dict:

        { "key": "open_tcp_connections",
          "type": "file",
          "path": "/proc/net/tcp",
          "parser": "line_count" }

        { "key": "logged_in_users",
          "type": "command",
          "command": "who | wc -l" }

    Supported types:
        file    — read a numeric value from a file path.
                  parser='line_count': count non-header, non-empty lines.
                  parser='first_word': parse the first whitespace-delimited token.
        command — run a shell command; its stdout is coerced to float.

    Results land in metrics['dynamic'][key]. A failing spec is logged at DEBUG
    and skipped — it never blocks other specs.
    """

    def __init__(self, settings: dict) -> None:
        self.specs: list = settings.get("dynamic_collectors", [])

    def collect(self, metrics: dict) -> None:
        """Evaluate all configured specs and merge results into metrics['dynamic']."""
        if not self.specs:
            return
        results: dict = {}
        for spec in self.specs:
            key = spec.get("key")
            ctype = spec.get("type")
            if not key or not ctype:
                continue
            try:
                value = self._collect_one(spec)
                if value is not None:
                    results[key] = value
            except Exception as exc:
                log.debug("DynamicCollector[%s]: %s", key, exc)
        if results:
            metrics["dynamic"] = results

    def _collect_one(self, spec: dict) -> Optional[float]:
        ctype = spec["type"]
        if ctype == "file":
            return self._collect_file(spec)
        if ctype == "command":
            return self._collect_command(spec)
        return None

    def _collect_file(self, spec: dict) -> Optional[float]:
        path = spec.get("path")
        if not path or not os.path.exists(path):
            return None
        parser = spec.get("parser", "first_word")
        with open(path) as fh:
            content = fh.read()
        if parser == "line_count":
            lines = [ln for ln in content.splitlines() if ln.strip()]
            return float(max(0, len(lines) - 1))  # subtract header row
        if parser == "first_word":
            tokens = content.split()
            return float(tokens[0]) if tokens else None
        return None

    def _collect_command(self, spec: dict) -> Optional[float]:
        command = spec.get("command", "")
        if not command:
            return None
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.strip()
        return float(output) if output else None

# Security watcher constants
# Directories watched by FileIntegrityWatcher (non-recursive).
FILE_INTEGRITY_WATCH_DIRS = [
    "/etc",
    "/bin",
    "/sbin",
    "/usr/bin",
    "/usr/sbin",
]

# Regex patterns matched against process names (case-insensitive).
SUSPICIOUS_PROCESS_PATTERNS = [
    r"(?i)^(nc|ncat|netcat)$",
    r"(?i)^(nmap|masscan|zmap)$",
    r"(?i)^(hydra|medusa|john|hashcat)$",
    r"(?i)(mimikatz|msfconsole|msfvenom|metasploit)",
    r"(?i)(cobaltstrike|cobalt_strike)",
    r"(?i)(bloodhound|sharphound)",
]

# Regex patterns matched against the full command line of new processes.
SUSPICIOUS_CMDLINE_PATTERNS = [
    r"-e\s+/bin/(ba)?sh",                   # netcat reverse shell handler
    r"bash\s+-i\s*>&",                       # interactive bash piped to socket
    r"/dev/tcp/",                            # bash TCP redirect shorthand
    r"base64\s+-d\s*\|",                     # base64-decode pipe (evasion)
    r"(curl|wget)[^\|]*\|\s*(ba)?sh",        # download-and-execute
    r"python[23]?\s+-c.*import\s+socket",   # python reverse shell boilerplate
    r"python[23]?\s+-c.*pty\.spawn",         # python TTY spawn
]

# Services whose unexpected absence triggers a service_stopped alert.
CRITICAL_SERVICES = [
    "sshd",
    "ufw",
    "firewalld",
    "auditd",
    "fail2ban",
    "rsyslog",
    "cron",
]

# Listening on these ports is flagged as a potential backdoor.
SUSPICIOUS_LISTEN_PORTS: frozenset = frozenset({4444, 4445, 5555, 6666, 6667, 1337, 31337, 9999})

# Auth log paths tried in order by LoginWatcher.
AUTH_LOG_PATHS = [
    "/var/log/auth.log",   # Debian / Ubuntu
    "/var/log/secure",     # RHEL / CentOS / Fedora
]

# Security watchers
class FileIntegrityWatcher:
    """
    Monitors critical system directories for unauthorised file changes.

    Uses watchdog (inotify on Linux, FSEvents on macOS) to receive real-time
    filesystem events. When a change is detected inside a watched directory,
    a signed alert is sent to the server.

    Directories : FILE_INTEGRITY_WATCH_DIRS
    Alert severities:
        file_modified  → high
        file_deleted   → high
        file_created   → medium
    """

    _SEVERITY: dict = {
        "file_modified": "high",
        "file_deleted": "high",
        "file_created": "medium",
    }

    def __init__(self, config: dict, settings: dict) -> None:
        self.config = config
        self.settings = settings

    def is_enabled(self) -> bool:
        return self.settings.get("watchers", {}).get("file_integrity", True)

    def start(self):
        """Start the watcher. Returns the Observer thread, or None if unavailable."""
        if not self.is_enabled():
            log.info("FileIntegrityWatcher: disabled in settings")
            return None
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            log.warning("FileIntegrityWatcher: watchdog not installed — disabled")
            return None

        watched_dirs = [d for d in FILE_INTEGRITY_WATCH_DIRS if os.path.isdir(d)]
        if not watched_dirs:
            log.warning("FileIntegrityWatcher: no watchable directories found — disabled")
            return None

        cfg = self.config
        severity_map = self._SEVERITY

        class _Handler(FileSystemEventHandler):
            def _alert(self, event_type: str, path: str) -> None:
                alert = {
                    "severity": severity_map.get(event_type, "medium"),
                    "event_type": event_type,
                    "details": {
                        "file_path": path,
                        "description": f"File integrity event in critical directory: {path}",
                    },
                }
                try:
                    send_alert(cfg, alert)
                    log.warning("FileIntegrity: %s → %s", event_type, path)
                except Exception as exc:
                    log.error("FileIntegrity: alert error for %s: %s", path, exc)

            def on_modified(self, event):
                if not event.is_directory:
                    self._alert("file_modified", event.src_path)

            def on_created(self, event):
                if not event.is_directory:
                    self._alert("file_created", event.src_path)

            def on_deleted(self, event):
                if not event.is_directory:
                    self._alert("file_deleted", event.src_path)

            def on_moved(self, event):
                if not event.is_directory:
                    self._alert("file_deleted", event.src_path)
                    self._alert("file_created", event.dest_path)

        handler = _Handler()
        observer = Observer()
        for d in watched_dirs:
            observer.schedule(handler, d, recursive=False)
        observer.daemon = True
        observer.start()
        log.info("FileIntegrityWatcher: active on %d director(ies)", len(watched_dirs))
        return observer  # Observer is a Thread subclass — safe to register with WatchdogCollector

class ProcessWatcher:
    """
    Polls the running process list and alerts on suspicious new processes.

    On each cycle, new PIDs are checked against SUSPICIOUS_PROCESS_PATTERNS
    (name) and SUSPICIOUS_CMDLINE_PATTERNS (command line). Matches trigger a
    process_started alert.
    """

    def __init__(self, config: dict, settings: dict) -> None:
        self.config = config
        self.settings = settings
        self._known_pids: set = set()

    def is_enabled(self) -> bool:
        return self.settings.get("watchers", {}).get("process", True)

    def _is_suspicious(self, name: str, cmdline: str) -> Optional[str]:
        for pattern in SUSPICIOUS_PROCESS_PATTERNS:
            if re.search(pattern, name or ""):
                return f"suspicious name matched: {pattern}"
        for pattern in SUSPICIOUS_CMDLINE_PATTERNS:
            if re.search(pattern, cmdline or ""):
                return f"suspicious cmdline matched: {pattern}"
        return None

    def _run_loop(self, interval: int) -> None:
        try:
            self._known_pids = {p.pid for p in psutil.process_iter(["pid"])}
        except Exception:
            self._known_pids = set()

        while True:
            time.sleep(interval)
            try:
                current: dict = {}
                for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                    try:
                        current[proc.pid] = proc.info
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                for pid in set(current) - self._known_pids:
                    info = current[pid]
                    name = info.get("name") or ""
                    cmdline = " ".join(info.get("cmdline") or [])
                    reason = self._is_suspicious(name, cmdline)
                    if reason:
                        alert = {
                            "severity": "high",
                            "event_type": "process_started",
                            "details": {
                                "process_name": name,
                                "process_id": pid,
                                "command_line": cmdline[:512],
                                "description": f"Suspicious process detected — {reason}",
                            },
                        }
                        try:
                            send_alert(self.config, alert)
                            log.warning("ProcessWatcher: PID %d (%s) — %s", pid, name, reason)
                        except Exception as exc:
                            log.error("ProcessWatcher: alert error PID %d: %s", pid, exc)

                self._known_pids = set(current)
            except Exception as exc:
                log.error("ProcessWatcher: poll error: %s", exc)

    def start(self, interval: int = 10) -> Optional[threading.Thread]:
        if not self.is_enabled():
            log.info("ProcessWatcher: disabled in settings")
            return None
        t = threading.Thread(
            target=self._run_loop, args=(interval,), daemon=True, name="process-watcher"
        )
        t.start()
        log.info("ProcessWatcher: started (poll=%ds)", interval)
        return t

class NetworkWatcher:
    """
    Monitors active network connections for suspicious activity.

    Polls psutil.net_connections() and flags any process listening on a port
    in SUSPICIOUS_LISTEN_PORTS. An alert-seen cache prevents flooding; the
    gate resets when the condition clears so repeat occurrences are reported.
    """

    def __init__(self, config: dict, settings: dict) -> None:
        self.config = config
        self.settings = settings
        self._alerted: set = set()

    def is_enabled(self) -> bool:
        return self.settings.get("watchers", {}).get("network", True)

    def _check_connections(self) -> None:
        try:
            conns = psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, Exception) as exc:
            log.debug("NetworkWatcher: net_connections error: %s", exc)
            return

        active_keys: set = set()
        for conn in conns:
            lport = conn.laddr.port if conn.laddr else None
            if conn.status == "LISTEN" and lport in SUSPICIOUS_LISTEN_PORTS:
                key = ("listen", lport)
                active_keys.add(key)
                if key not in self._alerted:
                    self._alerted.add(key)
                    alert = {
                        "severity": "critical",
                        "event_type": "network_connection",
                        "details": {
                            "description": (
                                f"Process listening on suspicious port {lport}"
                                " — possible backdoor"
                            ),
                            "destination_port": lport,
                            "protocol": "TCP",
                        },
                    }
                    try:
                        send_alert(self.config, alert)
                        log.warning("NetworkWatcher: suspicious LISTEN on port %d", lport)
                    except Exception as exc:
                        log.error("NetworkWatcher: alert error: %s", exc)

        # Clear gate for ports no longer listening so re-appearance is re-alerted
        self._alerted &= active_keys

    def _run_loop(self, interval: int) -> None:
        while True:
            time.sleep(interval)
            try:
                self._check_connections()
            except Exception as exc:
                log.error("NetworkWatcher: loop error: %s", exc)

    def start(self, interval: int = 15) -> Optional[threading.Thread]:
        if not self.is_enabled():
            log.info("NetworkWatcher: disabled in settings")
            return None
        t = threading.Thread(
            target=self._run_loop, args=(interval,), daemon=True, name="network-watcher"
        )
        t.start()
        log.info("NetworkWatcher: started (poll=%ds)", interval)
        return t

class LoginWatcher:
    """
    Monitors authentication logs for brute-force login attempts.

    Tails /var/log/auth.log (Debian/Ubuntu) or /var/log/secure (RHEL/CentOS).
    When failure count from a single source IP exceeds LOGIN_FAIL_THRESHOLD
    within LOGIN_FAIL_WINDOW seconds a login_failed alert is fired.
    Handles log rotation transparently via inode comparison.
    """

    LOGIN_FAIL_THRESHOLD: int = 10
    LOGIN_FAIL_WINDOW: int = 60  # seconds

    def __init__(self, config: dict, settings: dict) -> None:
        self.config = config
        self.settings = settings
        self._fail_times: dict = {}  # ip -> list[float]

    def is_enabled(self) -> bool:
        return self.settings.get("watchers", {}).get("login", True)

    def _find_log(self) -> Optional[str]:
        for path in AUTH_LOG_PATHS:
            if os.path.isfile(path):
                return path
        return None

    def _parse_ip(self, line: str) -> Optional[str]:
        """Return source IP if the line records a failed auth event, else None."""
        if "Failed password" not in line and "authentication failure" not in line.lower():
            return None
        m = re.search(r"from\s+([\d.]+)", line)
        return m.group(1) if m else "unknown"

    def _record_failure(self, ip: str) -> int:
        now = time.time()
        times = [t for t in self._fail_times.get(ip, []) if now - t < self.LOGIN_FAIL_WINDOW]
        times.append(now)
        self._fail_times[ip] = times
        return len(times)

    def _tail_loop(self, path: str, poll: int) -> None:
        # We hold a raw file handle (not a context manager) intentionally: the
        # handle needs to stay open across the entire while-loop so we can tail
        # new lines as they arrive, and we replace it in-place when log rotation
        # is detected. A 'with' block would close the file immediately.
        try:
            fh = open(path, "r")
            fh.seek(0, 2)  # jump to end — only watch new lines
        except OSError as exc:
            log.warning("LoginWatcher: cannot open %s: %s", path, exc)
            return

        log.info("LoginWatcher: tailing %s", path)
        alerted_ips: set = set()
        while True:
            time.sleep(poll)
            try:
                for line in fh:
                    ip = self._parse_ip(line)
                    if ip is None:
                        continue
                    count = self._record_failure(ip)
                    if count >= self.LOGIN_FAIL_THRESHOLD and ip not in alerted_ips:
                        alerted_ips.add(ip)
                        alert = {
                            "severity": "high",
                            "event_type": "login_failed",
                            "details": {
                                "description": (
                                    f"Brute-force SSH detected: {count} failures "
                                    f"from {ip} in the last {self.LOGIN_FAIL_WINDOW}s"
                                ),
                                "source_ip": ip,
                                "attempt_count": count,
                            },
                        }
                        try:
                            send_alert(self.config, alert)
                            log.warning(
                                "LoginWatcher: brute-force from %s (%d failures)", ip, count
                            )
                        except Exception as exc:
                            log.error("LoginWatcher: alert error: %s", exc)
                    elif count < self.LOGIN_FAIL_THRESHOLD:
                        alerted_ips.discard(ip)

                # Handle log rotation: reopen if inode changed
                try:
                    if os.stat(path).st_ino != os.fstat(fh.fileno()).st_ino:
                        fh.close()
                        fh = open(path, "r")
                        log.info("LoginWatcher: log rotated — reopened %s", path)
                except OSError:
                    pass
            except Exception as exc:
                log.error("LoginWatcher: error in tail loop: %s", exc)

    def start(self, poll: int = 5) -> Optional[threading.Thread]:
        if not self.is_enabled():
            log.info("LoginWatcher: disabled in settings")
            return None
        if sys.platform.startswith("win"):
            log.info("LoginWatcher: not supported on Windows")
            return None
        log_path = self._find_log()
        if not log_path:
            log.warning("LoginWatcher: no auth log found at %s — disabled", AUTH_LOG_PATHS)
            return None
        t = threading.Thread(
            target=self._tail_loop, args=(log_path, poll), daemon=True, name="login-watcher"
        )
        t.start()
        return t

class ServiceWatcher:
    """
    Monitors critical services for unexpected state transitions.

    Polls systemctl (Linux/systemd) or psutil process names (fallback) to
    determine whether each entry in CRITICAL_SERVICES is active. Fires a
    service_stopped alert on the first cycle a service transitions from
    active → inactive, then resets so a recurring stop is re-reported.
    """

    def __init__(self, config: dict, settings: dict) -> None:
        self.config = config
        self.settings = settings
        self._was_running: dict = {}

    def is_enabled(self) -> bool:
        return self.settings.get("watchers", {}).get("service", True)

    def _is_active(self, name: str) -> bool:
        if sys.platform.startswith("linux"):
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", "--quiet", name],
                    capture_output=True,
                    timeout=5,
                )
                return result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        # Cross-platform fallback: scan process names
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info.get("name") and name.lower() in proc.info["name"].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    def _run_loop(self, interval: int) -> None:
        for svc in CRITICAL_SERVICES:
            self._was_running[svc] = self._is_active(svc)

        while True:
            time.sleep(interval)
            for svc in CRITICAL_SERVICES:
                try:
                    active = self._is_active(svc)
                    if self._was_running.get(svc, True) and not active:
                        alert = {
                            "severity": "high",
                            "event_type": "service_stopped",
                            "details": {
                                "service_name": svc,
                                "description": f"Critical service '{svc}' stopped unexpectedly",
                            },
                        }
                        try:
                            send_alert(self.config, alert)
                            log.warning("ServiceWatcher: '%s' stopped — alert sent", svc)
                        except Exception as exc:
                            log.error("ServiceWatcher: alert error for '%s': %s", svc, exc)
                    self._was_running[svc] = active
                except Exception as exc:
                    log.error("ServiceWatcher: error checking '%s': %s", svc, exc)

    def start(self, interval: int = 60) -> Optional[threading.Thread]:
        if not self.is_enabled():
            log.info("ServiceWatcher: disabled in settings")
            return None
        t = threading.Thread(
            target=self._run_loop, args=(interval,), daemon=True, name="service-watcher"
        )
        t.start()
        log.info("ServiceWatcher: started — monitoring %d services", len(CRITICAL_SERVICES))
        return t


# Watchdog collector  —  meta-monitor for the monitoring pipeline
class WatchdogCollector:
    """
    Monitors the health of the monitoring pipeline itself.

    A watchdog collector is a meta-monitor: instead of collecting OS metrics
    it tracks whether collectors and watcher threads are alive and the send
    pipeline is functioning correctly.

    Responsibilities:
    - Register watcher threads and check their liveness on a background thread.
    - Append watchdog health fields to each telemetry payload via collect().
    - Send a 'custom' alert when any registered watcher thread dies.
    - Expose consecutive-failure count and time-since-last-send so the
      dashboard can detect silently-failing clients.

    Usage::

        watchdog = WatchdogCollector(config)
        thread = some_watcher.start()
        if thread:
            watchdog.register("some-watcher", thread)
        watchdog.start()

        # Inside the main telemetry loop:
        metrics = collect_metrics(settings, watchdog)
        try:
            send_telemetry(config, metrics)
            watchdog.record_success()
        except Exception:
            watchdog.record_failure()
    """

    def __init__(self, config: dict) -> None:
        self.config = config
        self._watchers: list = []             # list[(name, thread)]
        self._last_send_ts: float = time.time()
        self._consecutive_failures: int = 0
        self._alerted_dead: set = set()       # names already alerted so we don't repeat

    def register(self, name: str, thread) -> None:
        """Register a watcher thread to be monitored for liveness."""
        self._watchers.append((name, thread))

    def record_success(self) -> None:
        """Call after each successful telemetry send."""
        self._last_send_ts = time.time()
        self._consecutive_failures = 0

    def record_failure(self) -> None:
        """Call after each failed telemetry send attempt."""
        self._consecutive_failures += 1

    def collect(self, metrics: dict) -> None:
        """
        Append watchdog health fields to an existing metrics dict.

        Fields added:
            watchdog_seconds_since_send   — seconds since last successful send
            watchdog_consecutive_failures — consecutive failed send attempts
            watchdog_dead_watcher_count   — number of watcher threads that have stopped
            watchdog_dead_watchers        — names of dead threads (only if any)
        """
        dead = [n for n, t in self._watchers if not t.is_alive()]
        metrics["watchdog_seconds_since_send"] = int(time.time() - self._last_send_ts)
        metrics["watchdog_consecutive_failures"] = self._consecutive_failures
        metrics["watchdog_dead_watcher_count"] = len(dead)
        if dead:
            metrics["watchdog_dead_watchers"] = dead

    def _check_loop(self, interval: int) -> None:
        while True:
            time.sleep(interval)
            for name, thread in self._watchers:
                if not thread.is_alive() and name not in self._alerted_dead:
                    self._alerted_dead.add(name)
                    alert = {
                        "severity": "high",
                        "event_type": "custom",
                        "details": {
                            "description": (
                                f"Security watcher '{name}' has stopped unexpectedly. "
                                "Monitoring coverage may be reduced."
                            ),
                            "component": name,
                        },
                    }
                    try:
                        send_alert(self.config, alert)
                        log.error("WatchdogCollector: '%s' is dead — alert sent", name)
                    except Exception as exc:
                        log.error(
                            "WatchdogCollector: alert error for '%s': %s", name, exc
                        )

    def start(self, check_interval: int = 60) -> None:
        """Launch the background liveness-check thread."""
        t = threading.Thread(
            target=self._check_loop,
            args=(check_interval,),
            daemon=True,
            name="watchdog-collector",
        )
        t.start()
        log.info("WatchdogCollector: started (check_interval=%ds)", check_interval)


def start_security_watchers(
    config: dict, settings: dict, watchdog: WatchdogCollector
) -> None:
    """
    Initialise and start all security watcher threads.

    Each watcher that successfully starts returns its thread, which is
    registered with the WatchdogCollector for continuous liveness monitoring.
    """
    watcher_instances = [
        ("file-integrity-watcher", FileIntegrityWatcher(config, settings)),
        ("process-watcher",        ProcessWatcher(config, settings)),
        ("network-watcher",        NetworkWatcher(config, settings)),
        ("login-watcher",          LoginWatcher(config, settings)),
        ("service-watcher",        ServiceWatcher(config, settings)),
    ]
    for name, watcher in watcher_instances:
        thread = watcher.start()
        if thread is not None:
            watchdog.register(name, thread)


# Main loop

def run() -> None:
    config = load_config()
    settings = load_settings()

    # Register if credentials are missing
    if not config.get("client_id") or not config.get("secret_key"):
        retry_delay = 10
        while True:
            try:
                config = register(config)
                break
            except Exception as exc:
                log.error("Registration failed: %s — retrying in %ds", exc, retry_delay)
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 300)

    interval = settings.get("interval", 120)
    log.info("Starting telemetry loop (interval=%ds)", interval)

    # Start honeypot file watchers (canary-file access detection)
    start_honeypot_watcher(config)

    # Initialise the watchdog collector before starting security watchers so
    # every watcher thread can be registered immediately on start.
    watchdog = WatchdogCollector(config)
    start_security_watchers(config, settings, watchdog)
    watchdog.start()

    consecutive_auth_failures = 0

    while True:
        try:
            metrics = collect_metrics(settings, watchdog)
            result = send_telemetry(config, metrics)
            watchdog.record_success()
            consecutive_auth_failures = 0
            log.info(
                "Telemetry sent. ack_id=%s next_report_in=%s",
                result.get("ack_id"),
                result.get("next_report_in"),
            )

            # Apply any settings pushed from the dashboard
            pushed = result.get("settings")
            if pushed:
                settings, changed = apply_remote_settings(settings, pushed)
                if changed:
                    save_settings(settings)
                    log.info("Settings updated from server: %s", pushed)

            # Always honour the server's next_report_in (reflects effective interval)
            interval = result.get("next_report_in", interval)

            # In demo mode, opportunistically submit a synthetic alert.
            if settings.get("demo_mode") == "simulated":
                send_demo_alert(config, settings, interval)

        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            watchdog.record_failure()
            if status == 401:
                consecutive_auth_failures += 1
                log.warning("Auth failure #%d (401)", consecutive_auth_failures)
                try:
                    body = exc.response.json()
                except Exception:
                    body = {}
                error_msg = body.get("error", "")
                if "timestamp" in error_msg.lower():
                    log.warning("Clock skew detected — retrying without re-registering")
                elif consecutive_auth_failures >= 3:
                    log.warning("Clearing credentials and re-registering …")
                    config["client_id"] = ""
                    config["secret_key"] = ""
                    save_config(config)
                    try:
                        config = register(config)
                        consecutive_auth_failures = 0
                    except Exception as reg_exc:
                        log.error("Re-registration failed: %s", reg_exc)
            else:
                log.error("HTTP error %s: %s", status, exc)

        except requests.ConnectionError as exc:
            watchdog.record_failure()
            log.warning("Connection error: %s — will retry next cycle", exc)

        except Exception as exc:
            watchdog.record_failure()
            log.error("Unexpected error: %s", exc)

        time.sleep(interval)


if __name__ == "__main__":
    run()
