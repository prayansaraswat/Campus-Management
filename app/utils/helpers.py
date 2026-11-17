import random
import string
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_tracking_number() -> str:
    """Generate a unique tracking number for a concern, e.g., CC-2026-7824."""
    year = utc_now().year
    suffix = "".join(random.choices(string.digits, k=5))
    return f"CC-{year}-{suffix}"


def time_ago(dt: datetime) -> str:
    """Return a human-friendly relative time string."""
    if not dt:
        return ""
    # Ensure dt is naive UTC for difference calculation
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    now = utc_now()
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    return dt.strftime("%b %d, %Y")
