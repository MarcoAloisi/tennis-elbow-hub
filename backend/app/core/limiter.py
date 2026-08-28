"""Rate limiter configuration.

This module provides a centralized Limiter instance to be used across the application.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Keyed on request.client.host, i.e. get_remote_address(). Behind Cloudflare -> nginx
# -> uvicorn, that's only the real visitor IP (not the shared Cloudflare edge IP that
# collapsed all visitors into one bucket) because infra/nginx.conf's real_ip_module
# config validates CF-Connecting-IP against Cloudflare's published ranges before
# trusting it (unspoofable - the connecting IP must actually be Cloudflare's), and
# infra/te4-backend.service's --proxy-headers/--forwarded-allow-ips trusts that one
# resolved hop from nginx. Do not read CF-Connecting-IP directly in app code: at this
# layer request.client.host is always nginx's own loopback connection, so there is no
# way to verify the header wasn't spoofed by a request hitting the origin directly.
limiter = Limiter(key_func=get_remote_address)
