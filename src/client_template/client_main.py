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
import hashlib
import hmac
import json
import logging
import math
import os
import platform
import random
import socket
import sys
import time
from typing import Optional

import psutil
import requests
import yaml

# When frozen by PyInstaller, __file__ points into the temp extraction dir.
# Both config files must live *next to* the executable so each deployment can
# have its own credentials and independently managed settings.
if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(_BASE_DIR, "config.yaml")
SETTINGS_PATH = os.path.join(_BASE_DIR, "settings.yaml")
CLIENT_VERSION = 0.1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("capcan-client")

DEFAULT_SETTINGS = {
    "interval": 300,
    "demo_mode": False,
    "demo_alerts_per_hour": 20,
    "collect": {
        "cpu": True,
        "memory": True,
        "disk": True,
        "network": True,
        "processes": True,
    },
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
        if isinstance(on_disk.get("interval"), (int, float)):
            merged["interval"] = int(on_disk["interval"])
        if isinstance(on_disk.get("demo_mode"), bool):
            merged["demo_mode"] = on_disk["demo_mode"]
        if isinstance(on_disk.get("demo_alerts_per_hour"), (int, float)):
            merged["demo_alerts_per_hour"] = int(on_disk["demo_alerts_per_hour"])
        if isinstance(on_disk.get("collect"), dict):
            for k in merged["collect"]:
                if isinstance(on_disk["collect"].get(k), bool):
                    merged["collect"][k] = on_disk["collect"][k]
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
    changed = False

    if "interval" in incoming and isinstance(incoming["interval"], (int, float)):
        new_interval = int(incoming["interval"])
        if new_interval != updated.get("interval"):
            updated["interval"] = new_interval
            changed = True

    if "demo_mode" in incoming and isinstance(incoming["demo_mode"], bool):
        if incoming["demo_mode"] != updated.get("demo_mode"):
            updated["demo_mode"] = incoming["demo_mode"]
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

    return updated, changed


def detect_platform() -> str:
    """Map sys.platform to a value the server accepts: linux / windows / macos."""
    s = sys.platform.lower()
    if s.startswith("linux"):
        return "linux"
    if s.startswith("win"):
        return "windows"
    if s in ("darwin",):
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
    import datetime as dt
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
_prev_disk_io: Optional[object] = None
_prev_net_io: Optional[object] = None

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


def collect_metrics(settings: dict) -> dict:
    """Collect a telemetry snapshot, respecting enabled/disabled collect flags."""
    if settings.get("demo_mode"):
        log.debug("Demo mode active — sending synthetic telemetry")
        return collect_demo_metrics(settings)

    global _prev_disk_io, _prev_net_io

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

        curr_disk = psutil.disk_io_counters()
        if curr_disk and _prev_disk_io:
            metrics["disk_read_bytes"] = max(0, curr_disk.read_bytes - _prev_disk_io.read_bytes)
            metrics["disk_write_bytes"] = max(0, curr_disk.write_bytes - _prev_disk_io.write_bytes)
        _prev_disk_io = curr_disk
    else:
        _prev_disk_io = None  # reset delta so re-enable doesn't spike

    if collect.get("network", True):
        curr_net = psutil.net_io_counters()
        if curr_net and _prev_net_io:
            metrics["network_sent_bytes"] = max(0, curr_net.bytes_sent - _prev_net_io.bytes_sent)
            metrics["network_recv_bytes"] = max(0, curr_net.bytes_recv - _prev_net_io.bytes_recv)
        _prev_net_io = curr_net
    else:
        _prev_net_io = None  # reset delta so re-enable doesn't spike

    if collect.get("processes", True):
        metrics["process_count"] = len(psutil.pids())

    if hasattr(os, "getloadavg"):
        la = os.getloadavg()
        metrics["load_average"] = [round(x, 2) for x in la]

    metrics["uptime_seconds"] = int(time.time() - psutil.boot_time())
    metrics["platform"] = detect_platform()
    metrics["hostname"] = socket.gethostname()

    return metrics


# Telemetry send

def send_telemetry(config: dict, metrics: dict) -> dict:
    """
    Sign and POST telemetry data to the server.
    Returns the parsed JSON response on success.
    Raises requests.HTTPError on HTTP error responses.
    """
    url = config["server_url"].rstrip("/") + "/api/v1/telemetry/"
    body_bytes = json.dumps(metrics, separators=(",", ":")).encode("utf-8")
    headers = sign_request(config["client_id"], config["secret_key"], body_bytes)

    resp = requests.post(url, data=body_bytes, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def send_alert(config: dict, alert_data: dict) -> dict:
    """
    Sign and POST a single alert to the server.
    Uses the same HMAC scheme as send_telemetry.
    Raises requests.HTTPError on HTTP error responses.
    """
    url = config["server_url"].rstrip("/") + "/api/v1/alerts/"
    body_bytes = json.dumps(alert_data, separators=(",", ":")).encode("utf-8")
    headers = sign_request(config["client_id"], config["secret_key"], body_bytes)

    resp = requests.post(url, data=body_bytes, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _maybe_send_demo_alert(config: dict, settings: dict, interval: int) -> None:
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

    interval = settings.get("interval", 300)
    log.info("Starting telemetry loop (interval=%ds)", interval)

    consecutive_auth_failures = 0

    while True:
        try:
            metrics = collect_metrics(settings)
            result = send_telemetry(config, metrics)
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
            if settings.get("demo_mode"):
                _maybe_send_demo_alert(config, settings, interval)

        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
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
            log.warning("Connection error: %s — will retry next cycle", exc)

        except Exception as exc:
            log.error("Unexpected error: %s", exc)

        time.sleep(interval)


if __name__ == "__main__":
    run()
