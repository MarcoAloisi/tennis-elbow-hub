"""Structured logging configuration.

Provides consistent logging format across the application
with support for different log levels based on environment.
"""

import logging
import re
import sys

from app.core.config import get_settings

# Matches a `token=...` query-string value up to the next `&`, quote, or
# whitespace, so it can be redacted wherever it shows up in a log line.
_TOKEN_QUERY_PARAM_RE = re.compile(r"token=[^&\"\s]+")


def _redact_token(value: object) -> object:
    """Redact a `token=...` query-string value in a string, leave other values untouched."""
    if isinstance(value, str) and "token=" in value:
        return _TOKEN_QUERY_PARAM_RE.sub("token=***REDACTED***", value)
    return value


class _RedactTokenFilter(logging.Filter):
    """Redacts presence-token query strings from uvicorn's access log.

    The presence WebSocket endpoint necessarily carries its auth token as a
    `?token=...` URL query param (browsers can't set WS handshake headers).
    nginx's `access_log off` on that location keeps nginx from persisting it,
    but uvicorn's own `uvicorn.access` logger independently logs every
    accepted connection's path (including the query string) to stdout, which
    lands in the systemd journal. This filter redacts it before emission.

    uvicorn's exact message/args format can vary, so instead of matching a
    specific message string, this inspects every positional/keyword arg
    attached to the record (uvicorn logs the path as one of the `%s` args)
    and redacts any `token=...` found in a string arg, plus the raw message
    itself as a fallback.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: _redact_token(v) for k, v in record.args.items()}
            else:
                record.args = tuple(_redact_token(a) for a in record.args)
        if isinstance(record.msg, str):
            record.msg = _redact_token(record.msg)
        return True


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

    # Redact presence-token query strings from uvicorn's access log, which
    # is otherwise untouched by the app's own logging config (see
    # _RedactTokenFilter docstring). Guard against double-registration in
    # case setup_logging() ever runs more than once in a process.
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, _RedactTokenFilter) for f in uvicorn_access_logger.filters):
        uvicorn_access_logger.addFilter(_RedactTokenFilter())

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
