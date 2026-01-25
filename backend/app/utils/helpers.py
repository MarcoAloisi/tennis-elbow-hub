"""General utility helper functions."""

from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    """Get current UTC datetime.

    Returns:
        Current datetime in UTC timezone.
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Get current UTC datetime as ISO string.

    Returns:
        ISO 8601 formatted string.
    """
    return utc_now().isoformat()


def safe_get(data: dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get a value from a dictionary.

    Args:
        data: Dictionary to get value from.
        key: Key to look up.
        default: Default value if key not found.

    Returns:
        Value at key or default.
    """
    return data.get(key, default)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max.

    Args:
        value: Value to clamp.
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.

    Returns:
        Clamped value.
    """
    return max(min_val, min(max_val, value))


def percentage(numerator: int, denominator: int) -> float:
    """Calculate percentage safely.

    Args:
        numerator: Top of the fraction.
        denominator: Bottom of the fraction.

    Returns:
        Percentage value (0-100), or 0 if denominator is 0.
    """
    if denominator == 0:
        return 0.0
    return round(numerator / denominator * 100, 1)
