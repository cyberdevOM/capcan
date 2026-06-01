"""
Telemetry cache — rolling in-memory + on-disk cache of the last N telemetry
snapshots per client.

The cache is the primary source for telemetry analysis (spike detection,
sustained-high detection, alert correlation) so the database is only hit for
historical queries, not every incoming submission.

Layout:
  CACHE_FILE  →  { client_id: [ {telemetry: {...}, timestamp: "ISO"}, ... ] }
  newest entry is always at index 0 (prepend on push).

Thread-safety: a single module-level Lock guards all reads and writes.
"""

import json
import os
import threading
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WINDOW_SIZE = 5   # snapshots retained per client

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
CACHE_FILE = os.path.join(_REPO_ROOT, 'data', 'telemetry_cache.json')

_lock: threading.Lock = threading.Lock()

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load() -> dict:
    """Read cache from disk. Returns empty dict on any read/parse error."""
    try:
        with open(CACHE_FILE, 'r') as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(cache: dict) -> None:
    """Atomically write cache to disk."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    tmp = CACHE_FILE + '.tmp'
    with open(tmp, 'w') as fh:
        json.dump(cache, fh)
    os.replace(tmp, CACHE_FILE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def push(client_id: str, telemetry: dict, timestamp: str | None = None) -> None:
    """
    Prepend a new snapshot for *client_id* and trim to WINDOW_SIZE.
    *timestamp* defaults to current UTC time if not provided.
    """
    entry = {
        'telemetry': telemetry,
        'timestamp': timestamp or datetime.utcnow().isoformat(),
    }
    with _lock:
        cache = _load()
        window = cache.get(client_id, [])
        window.insert(0, entry)
        cache[client_id] = window[:WINDOW_SIZE]
        _save(cache)


def get(client_id: str) -> list[dict]:
    """
    Return the cached window for *client_id* (newest first).
    Returns an empty list if no data is cached yet.
    """
    with _lock:
        return _load().get(client_id, [])


def get_all() -> dict:
    """Return the full cache dict (all clients)."""
    with _lock:
        return _load()


def evict(client_id: str) -> None:
    """Remove all cached entries for a client (e.g. on client deletion)."""
    with _lock:
        cache = _load()
        if client_id in cache:
            del cache[client_id]
            _save(cache)
