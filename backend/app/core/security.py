"""Security utilities and middleware configuration.

This module provides:
- Input sanitization helpers
- File upload validation (HTML and images)
- Security middleware setup
- Rate limiting configuration
"""

import re
from pathlib import Path

import nh3
from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


# Allowed HTML tags for guide content sanitization (TipTap output)
ALLOWED_TAGS: set[str] = {
    "p", "br", "strong", "em", "u", "s",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "a", "blockquote", "pre", "code",
    "img", "hr",
}
ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "a": {"href", "target", "rel"},
    "img": {"src", "alt", "title"},
}

# Allowed file extensions for HTML upload
ALLOWED_EXTENSIONS: set[str] = {".html", ".htm"}

# Allowed MIME types for HTML upload
ALLOWED_MIME_TYPES: set[str] = {
    "text/html",
    "text/htm",
    "application/xhtml+xml",
}

# Allowed image extensions
ALLOWED_IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# Allowed image MIME types
ALLOWED_IMAGE_MIME_TYPES: set[str] = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
}


def sanitize_html(content: str) -> str:
    """Sanitize HTML content by removing potentially dangerous tags.

    Args:
        content: Raw HTML content to sanitize.

    Returns:
        Sanitized HTML string with dangerous content removed.
    """
    return nh3.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
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
    """Validate an uploaded HTML file for security.

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
    content_length = file.size
    if content_length and content_length > settings.max_upload_size_bytes:
         raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )

    # 2. Chunked Reading (Robust Fail)
    max_size = settings.max_upload_size_bytes
    current_size = 0
    chunks = []

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

    return b"".join(chunks)


async def validate_image_upload(file: UploadFile, max_size_mb: int = 5) -> bytes:
    """Validate an uploaded image file for security.

    Checks:
    - Filename presence
    - Extension whitelist (png, jpg, jpeg, gif, webp)
    - MIME type whitelist
    - Size limit via chunked reading

    Args:
        file: FastAPI UploadFile object.
        max_size_mb: Maximum file size in megabytes.

    Returns:
        File contents as bytes if validation passes.

    Raises:
        HTTPException: If file validation fails.
    """
    # Check filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Check extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image type not allowed. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
        )

    # Check MIME type (if provided)
    if file.content_type and file.content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image MIME type not allowed: {file.content_type}",
        )

    # Size check + chunked reading
    max_size = max_size_mb * 1024 * 1024

    # Fast fail via reported size
    if file.size and file.size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image too large. Maximum size: {max_size_mb}MB",
        )

    # Robust chunked reading
    current_size = 0
    chunks = []
    CHUNK_SIZE = 1024 * 1024

    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break

        current_size += len(chunk)
        if current_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Image too large. Maximum size: {max_size_mb}MB",
            )
        chunks.append(chunk)

    content = b"".join(chunks)

    # Validate magic bytes to ensure file is a real image
    if not _has_valid_image_magic_bytes(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match a valid image format.",
        )

    return content


def _has_valid_image_magic_bytes(data: bytes) -> bool:
    """Check if file content starts with known image magic bytes.

    Args:
        data: Raw file bytes.

    Returns:
        True if the file signature matches a known image format.
    """
    if len(data) < 12:
        return False

    # PNG: \x89PNG\r\n\x1a\n
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    # JPEG: \xff\xd8\xff
    if data[:3] == b"\xff\xd8\xff":
        return True
    # GIF: GIF87a or GIF89a
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    # WebP: RIFF....WEBP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True

    return False


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
        "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://tagmanager.google.com https://www.google-analytics.com https://ssl.google-analytics.com https://pagead2.googlesyndication.com https://tagassistant.google.com https://fundingchoicesmessages.google.com",
        # Styles: Fonts, GTM
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://tagmanager.google.com",
        # Images: GTM, Analytics, AdSense, Google Ads
        "img-src 'self' data: https://*.supabase.co https://www.googletagmanager.com https://ssl.gstatic.com https://www.google-analytics.com https://pagead2.googlesyndication.com https://img.youtube.com https://www.google.com",
        # Fonts: Google Fonts
        "font-src 'self' data: https://fonts.gstatic.com",
        # Connect: Analytics, GTM, Tag Assistant, Google Ads
        "connect-src 'self' https://www.google-analytics.com https://region1.google-analytics.com https://www.googletagmanager.com https://tagassistant.google.com https://stats.g.doubleclick.net https://www.google.com https://fundingchoicesmessages.google.com",
        # Frames: GTM (noscript), AdSense
        "frame-src 'self' https://www.googletagmanager.com https://googleads.g.doubleclick.net https://tpc.googlesyndication.com https://fundingchoicesmessages.google.com https://www.youtube.com",
        # Security Hardening
        "frame-ancestors 'none'",  # Prevent clickjacking
        "object-src 'none'",       # Block Flash/Java
        "base-uri 'self'",         # Prevent base tag hijacking
    ]

    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
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
