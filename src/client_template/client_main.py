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
  2. If not yet registered, POST to /api/clients/register and save credentials
  3. Loop: collect metrics → sign with HMAC → POST to /api/telemetry/
           → apply any settings pushed from dashboard → sleep
"""

import hashlib
import hmac
import json
import logging
import os
import platform
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

_DEFAULT_SETTINGS = {
    "interval": 300,
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
        merged = dict(_DEFAULT_SETTINGS)
        merged["collect"] = dict(_DEFAULT_SETTINGS["collect"])
        if isinstance(on_disk.get("interval"), (int, float)):
            merged["interval"] = int(on_disk["interval"])
        if isinstance(on_disk.get("collect"), dict):
            for k in merged["collect"]:
                if isinstance(on_disk["collect"].get(k), bool):
                    merged["collect"][k] = on_disk["collect"][k]
        return merged
    except Exception:
        return dict(_DEFAULT_SETTINGS)


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
    updated["collect"] = dict(current.get("collect", _DEFAULT_SETTINGS["collect"]))
    changed = False

    if "interval" in incoming and isinstance(incoming["interval"], (int, float)):
        new_interval = int(incoming["interval"])
        if new_interval != updated.get("interval"):
            updated["interval"] = new_interval
            changed = True

    if "collect" in incoming and isinstance(incoming["collect"], dict):
        for key in _DEFAULT_SETTINGS["collect"]:
            if key in incoming["collect"] and isinstance(incoming["collect"][key], bool):
                if incoming["collect"][key] != updated["collect"].get(key):
                    updated["collect"][key] = incoming["collect"][key]
                    changed = True

    return updated, changed


def _detect_platform() -> str:
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
    url = config["server_url"].rstrip("/") + "/api/clients/register"
    payload = {
        "hostname": socket.gethostname(),
        "platform": _detect_platform(),
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


def collect_metrics(settings: dict) -> dict:
    """Collect a telemetry snapshot, respecting enabled/disabled collect flags."""
    global _prev_disk_io, _prev_net_io

    collect = settings.get("collect", _DEFAULT_SETTINGS["collect"])
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

    return metrics


# Telemetry send

def send_telemetry(config: dict, metrics: dict) -> dict:
    """
    Sign and POST telemetry data to the server.
    Returns the parsed JSON response on success.
    Raises requests.HTTPError on HTTP error responses.
    """
    url = config["server_url"].rstrip("/") + "/api/telemetry/"
    body_bytes = json.dumps(metrics, separators=(",", ":")).encode("utf-8")
    headers = sign_request(config["client_id"], config["secret_key"], body_bytes)

    resp = requests.post(url, data=body_bytes, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


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


import hashlib
import hmac
import json
import logging
import os
import platform
import socket
import sys
import time
from typing import Optional

import psutil
import requests
import yaml

# When frozen by PyInstaller, __file__ points into the temp extraction dir.
# Config must live *next to* the executable so each deployment can have its own credentials.
if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_BASE_DIR, "config.yaml")
CLIENT_VERSION = 0.1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("capcan-client")


# Config helpers 

def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

def _detect_platform() -> str:
    """Map sys.platform to a value the server accepts: linux / windows / macos."""
    s = sys.platform.lower()
    if s.startswith("linux"):
        return "linux"
    if s.startswith("win"):
        return "windows"
    if s in ("darwin",):
        return "macos"
    # Fall back to whatever is in config
    return "linux"


def register(config: dict) -> dict:
    """
    Register this client with the server.
    Returns an updated config dict with client_id and secret_key populated.
    Raises on failure so the caller can decide whether to abort or retry.
    """
    url = config["server_url"].rstrip("/") + "/api/clients/register"
    payload = {
        "hostname": socket.gethostname(),
        "platform": _detect_platform(),
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

# Counters from the previous collection cycle (cumulative psutil values at boot,
# so we track deltas to report bytes-since-last-report as the server expects).
_prev_disk_io: Optional[object] = None
_prev_net_io: Optional[object] = None

# Warm up cpu_percent — first call always returns 0.0, second is accurate.
psutil.cpu_percent(interval=None)


def collect_metrics() -> dict:
    """Collect a telemetry snapshot. Counter fields are deltas since last call."""
    global _prev_disk_io, _prev_net_io

    metrics: dict = {}

    # CPU (non-blocking; warm-up call is done at module level)
    metrics["cpu_percent"] = round(psutil.cpu_percent(interval=1), 2)

    # Memory
    mem = psutil.virtual_memory()
    metrics["memory_percent"] = round(mem.percent, 2)
    metrics["memory_available"] = mem.available // (1024 * 1024)  # MB

    # Disk usage (root / on Linux, C:\ on Windows)
    root = "C:\\" if sys.platform.startswith("win") else "/"
    disk = psutil.disk_usage(root)
    metrics["disk_usage"] = round(disk.percent, 2)

    # Disk I/O deltas
    curr_disk = psutil.disk_io_counters()
    if curr_disk and _prev_disk_io:
        metrics["disk_read_bytes"] = max(0, curr_disk.read_bytes - _prev_disk_io.read_bytes)
        metrics["disk_write_bytes"] = max(0, curr_disk.write_bytes - _prev_disk_io.write_bytes)
    _prev_disk_io = curr_disk

    # Network I/O deltas
    curr_net = psutil.net_io_counters()
    if curr_net and _prev_net_io:
        metrics["network_sent_bytes"] = max(0, curr_net.bytes_sent - _prev_net_io.bytes_sent)
        metrics["network_recv_bytes"] = max(0, curr_net.bytes_recv - _prev_net_io.bytes_recv)
    _prev_net_io = curr_net

    # Processes
    metrics["process_count"] = len(psutil.pids())

    # Load average (Linux / macOS only)
    if hasattr(os, "getloadavg"):
        la = os.getloadavg()
        metrics["load_average"] = [round(x, 2) for x in la]

    # Uptime
    metrics["uptime_seconds"] = int(time.time() - psutil.boot_time())

    return metrics


# Telemetry send

def send_telemetry(config: dict, metrics: dict) -> dict:
    """
    Sign and POST telemetry data to the server.
    Returns the parsed JSON response on success.
    Raises requests.HTTPError on HTTP error responses.
    """
    url = config["server_url"].rstrip("/") + "/api/telemetry/"
    body_bytes = json.dumps(metrics, separators=(",", ":")).encode("utf-8")
    headers = sign_request(config["client_id"], config["secret_key"], body_bytes)

    resp = requests.post(url, data=body_bytes, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


# Main loop

def run() -> None:
    config = load_config()

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

    interval = config.get("interval", 60)
    log.info("Starting telemetry loop (interval=%ds)", interval)

    consecutive_auth_failures = 0

    while True:
        try:
            metrics = collect_metrics()
            result = send_telemetry(config, metrics)
            consecutive_auth_failures = 0
            log.info(
                "Telemetry sent. ack_id=%s next_report_in=%s",
                result.get("ack_id"),
                result.get("next_report_in"),
            )
            # Honour server's requested interval if provided
            interval = result.get("next_report_in", interval)

        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 401:
                consecutive_auth_failures += 1
                log.warning("Auth failure #%d (401)", consecutive_auth_failures)
                # Distinguish clock-skew (timestamp error) from unknown client
                try:
                    body = exc.response.json()
                except Exception:
                    body = {}
                error_msg = body.get("error", "")
                if "timestamp" in error_msg.lower():
                    # Clock skew — do not re-register, just retry
                    log.warning("Clock skew detected — retrying without re-registering")
                elif consecutive_auth_failures >= 3:
                    # Stale credentials — clear and re-register
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
