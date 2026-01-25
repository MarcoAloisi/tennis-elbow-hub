"""Structured logging configuration.

Provides consistent logging format across the application
with support for different log levels based on environment.
"""

import logging
import sys
from typing import Any

from app.core.config import get_settings


def setup_logging() -> logging.Logger:
    """Configure and return the application logger.

    Returns:
        Configured logger instance.
    """
    settings = get_settings()

    # Determine log level based on environment
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger
    logger = logging.getLogger("tennis_tracker")
    logger.setLevel(log_level)
    logger.addHandler(handler)

    # Prevent duplicate logs
    logger.propagate = False

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger instance with optional name suffix.

    Args:
        name: Optional suffix to append to logger name.

    Returns:
        Logger instance.
    """
    base_name = "tennis_tracker"
    logger_name = f"{base_name}.{name}" if name else base_name
    return logging.getLogger(logger_name)
