import datetime as dt

def get_current_timestamp():
    """Returns the current UTC timestamp in ISO 8601 format with 'Z' suffix."""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"

def parse_timestamp(timestamp_str):
    """Parses an ISO 8601 timestamp string and returns a datetime object."""
    try:
        return dt.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError as e:
        raise ValueError(f"Invalid timestamp format: {timestamp_str}. Expected ISO 8601 with 'Z' suffix.") from e

def format_timestamp(dt_obj) -> str:
    """Formats an existing datetime object to ISO 8601 with 'Z' suffix."""
    if dt_obj is None:
        return None
    if hasattr(dt_obj, 'isoformat'):
        return dt_obj.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
    return str(dt_obj)

def format_uptime(seconds: int) -> str:
    """Format an uptime duration in seconds to a compact human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        h, m = divmod(seconds, 3600)
        return f"{h}h {m // 60}m"
    d, rem = divmod(seconds, 86400)
    return f"{d}d {rem // 3600}h"
