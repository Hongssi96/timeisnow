"""Diagnostic source-age checks; callers must supply an explicit age policy."""
from datetime import datetime, timezone
import math


def assess_source_age(generated_at, fetched_at, max_age_seconds, source_timezone=None):
    if type(max_age_seconds) not in (int, float) or not math.isfinite(max_age_seconds) or max_age_seconds <= 0:
        raise ValueError("An explicit positive age limit is required")
    if not generated_at:
        return {"status": "unknown", "reason": "generation_time_missing", "age_seconds": None}
    try:
        generated = datetime.fromisoformat(generated_at) if isinstance(generated_at, str) else generated_at
        if not isinstance(generated, datetime):
            raise ValueError("invalid timestamp")
        if generated.tzinfo is None or generated.utcoffset() is None:
            if source_timezone is None:
                return {"status": "unknown", "reason": "generation_timezone_missing", "age_seconds": None}
            generated = generated.replace(tzinfo=source_timezone)
        if not isinstance(fetched_at, datetime) or fetched_at.tzinfo is None or fetched_at.utcoffset() is None:
            raise ValueError("aware receipt time required")
        age = (fetched_at.astimezone(timezone.utc) - generated.astimezone(timezone.utc)).total_seconds()
    except (ValueError, TypeError, OverflowError):
        return {"status": "unknown", "reason": "timestamp_invalid", "age_seconds": None}
    if age < 0:
        return {"status": "clock_mismatch", "reason": "generation_time_in_future", "age_seconds": age}
    return {"status": "stale" if age > max_age_seconds else "fresh", "reason": None, "age_seconds": age}
