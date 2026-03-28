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
    
