"""Rate limiter configuration.

This module provides a centralized Limiter instance to be used across the application.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def get_client_ip(request: Request) -> str:
    """Rate-limit key: prefer Cloudflare's true client IP over the raw peer address.

    Prod runs behind Cloudflare -> nginx -> uvicorn. Even with uvicorn's proxy-header
    trust covering the nginx hop, X-Forwarded-For's last entry is nginx's own
    $remote_addr - Cloudflare's edge IP, not the visitor's. That collapsed every
    visitor behind the same Cloudflare PoP into one shared rate-limit bucket.
    CF-Connecting-IP is set/overwritten by Cloudflare's edge itself, so it can't
    be spoofed by traffic that actually goes through Cloudflare.
    """
    cf_ip = request.headers.get("CF-Connecting-IP")
    return cf_ip if cf_ip else get_remote_address(request)


# Initialize rate limiter, keyed by the visitor's real IP (see get_client_ip)
limiter = Limiter(key_func=get_client_ip)
