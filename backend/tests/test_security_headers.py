"""Tests for HTTP security headers."""

from app.core.security import get_security_headers


def test_csp_connect_src_allows_google_collect_hosts() -> None:
    """GA4/Ads collect hosts that previously 404'd in the browser CSP."""
    csp = get_security_headers()["Content-Security-Policy"]
    required = (
        "https://region1.analytics.google.com",
        "https://ad.doubleclick.net",
        "https://www.google.es",
        "https://pagead2.googlesyndication.com",
        "https://googleads.g.doubleclick.net",
        "https://www.googleadservices.com",
    )
    for host in required:
        assert host in csp
