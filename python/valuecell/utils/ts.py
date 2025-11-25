from datetime import datetime, timezone


def get_current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)
