"""Security utilities and middleware configuration.

This module provides:
- Input sanitization helpers
- File upload validation
- Security middleware setup
- Rate limiting configuration
"""

import re
from pathlib import Path
from typing import Any

import bleach
from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


# Allowed HTML tags for sanitization (none by default for security)
ALLOWED_TAGS: list[str] = []
ALLOWED_ATTRIBUTES: dict[str, list[str]] = {}

# Allowed file extensions for upload
ALLOWED_EXTENSIONS: set[str] = {".html", ".htm"}

# Allowed MIME types for upload
ALLOWED_MIME_TYPES: set[str] = {
    "text/html",
    "text/htm",
    "application/xhtml+xml",
}


def sanitize_html(content: str) -> str:
    """Sanitize HTML content by removing potentially dangerous tags.

    Args:
        content: Raw HTML content to sanitize.

    Returns:
        Sanitized HTML string with dangerous content removed.
    """
    return bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal attacks.

    Args:
        filename: Original filename from upload.

    Returns:
        Safe filename with special characters removed.
    """
    # Remove path separators and null bytes
    safe_name = re.sub(r'[<>:"/\\|?*\x00]', "", filename)

    # Remove leading dots and spaces
    safe_name = safe_name.lstrip(". ")

    # Limit length
    max_length = 255
    if len(safe_name) > max_length:
        name_part = Path(safe_name).stem[:max_length - 10]
        ext_part = Path(safe_name).suffix[:10]
        safe_name = f"{name_part}{ext_part}"

    return safe_name or "unnamed_file"


async def validate_upload_file(file: UploadFile) -> bytes:
    """Validate an uploaded file for security.

    Checks:
    - Filename presence
    - Extension and MIME type whitelist
    - Size limit (via chunked reading to prevent Memory DoS)

    Args:
        file: FastAPI UploadFile object.

    Returns:
        File contents as bytes if validation passes.

    Raises:
        HTTPException: If file validation fails.
    """
    settings = get_settings()

    # Check filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Check extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Check MIME type (if provided)
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME type not allowed: {file.content_type}",
        )
    
    # 1. Check Content-Length Header (Fast Fail)
    # This is not trustable as it can be spoofed, but good for UX fail-fast
    content_length = file.size
    if content_length and content_length > settings.max_upload_size_bytes:
         raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )

    # 2. Chunked Reading (Robust Fail)
    # Read file in chunks to ensure we never load more than MAX + Buffer into RAM
    max_size = settings.max_upload_size_bytes
    current_size = 0
    chunks = []
    
    # Chunk size: 1MB or appropriately tuned
    CHUNK_SIZE = 1024 * 1024 
    
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
            
        current_size += len(chunk)
        if current_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
            )
        chunks.append(chunk)

    # Reassemble (safe now as size is confirmed < MAX)
    return b"".join(chunks)


def get_security_headers() -> dict[str, str]:
    """Get security headers for HTTP responses.

    Returns:
        Dictionary of security headers to add to responses.
    """
    # Content Security Policy (CSP) configuration
    # Note: 'unsafe-inline' and 'unsafe-eval' are required for GTM/AdSense to function.
    csp_directives = [
        "default-src 'self'",
        # Scripts: GTM, Analytics, AdSense, Tag Assistant
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://tagmanager.google.com https://www.google-analytics.com https://ssl.google-analytics.com https://pagead2.googlesyndication.com https://tagassistant.google.com",
        # Styles: Fonts, GTM
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://tagmanager.google.com",
        # Images: GTM, Analytics, AdSense
        "img-src 'self' data: https://www.googletagmanager.com https://ssl.gstatic.com https://www.google-analytics.com https://pagead2.googlesyndication.com",
        # Fonts: Google Fonts
        "font-src 'self' data: https://fonts.gstatic.com",
        # Connect: Analytics, GTM, Tag Assistant
        "connect-src 'self' https://www.google-analytics.com https://www.googletagmanager.com https://tagassistant.google.com https://stats.g.doubleclick.net",
        # Frames: GTM (noscript), AdSense
        "frame-src 'self' https://www.googletagmanager.com https://googleads.g.doubleclick.net https://tpc.googlesyndication.com",
        # Security Hardening
        "frame-ancestors 'none'",  # Prevent clickjacking
        "object-src 'none'",       # Block Flash/Java
        "base-uri 'self'",         # Prevent base tag hijacking
    ]

    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Content-Security-Policy": "; ".join(csp_directives),
    }


def validate_hex_string(value: str) -> bool:
    """Validate that a string contains only valid hexadecimal characters.

    Args:
        value: String to validate.

    Returns:
        True if valid hex string, False otherwise.
    """
    if not value:
        return False
    return bool(re.match(r"^[0-9A-Fa-f]+$", value))


def safe_int_from_hex(value: str, default: int = 0) -> int:
    """Safely convert a hex string to integer.

    Args:
        value: Hexadecimal string.
        default: Default value if conversion fails.

    Returns:
        Integer value or default.
    """
    try:
        return int(value, 16)
    except (ValueError, TypeError):
        return default
