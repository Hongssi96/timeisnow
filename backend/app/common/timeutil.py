"""UTC timestamps in the wire format used by the response envelope."""
from datetime import datetime, timezone


def iso(value):
    return value.isoformat(timespec='seconds').replace('+00:00', 'Z')


def utc_now_iso() -> str:
    return iso(datetime.now(timezone.utc))
