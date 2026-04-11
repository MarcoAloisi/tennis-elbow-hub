"""Shared utility functions."""


def escape_like(value: str) -> str:
    """Escape special LIKE/ILIKE pattern characters (% and _)."""
    return value.replace("%", r"\%").replace("_", r"\_")
