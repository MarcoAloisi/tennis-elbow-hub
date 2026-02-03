"""Rate limiter configuration.

This module provides a centralized Limiter instance to be used across the application.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize rate limiter with remote address as key
limiter = Limiter(key_func=get_remote_address)
