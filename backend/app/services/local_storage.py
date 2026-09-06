"""Local disk storage for uploaded images, replacing Supabase Storage.

Files land at ``{media_root}/{bucket}/{filename}`` and are served by nginx
under ``/media/{bucket}/{filename}`` — this module never serves reads itself.
"""

import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.security import compress_image, validate_image_upload


class UnsafePathError(ValueError):
    """Raised when a storage path attempts to escape its bucket directory."""


def _safe_dest(media_root: str, bucket: str, filename: str) -> Path:
    if filename.startswith("/") or ".." in Path(filename).parts:
        raise UnsafePathError(f"Unsafe storage path: {filename!r}")
    return Path(media_root) / bucket / filename


async def process_upload(file: UploadFile, max_size_mb: int = 5) -> tuple[bytes, str]:
    """Validate an uploaded image and re-encode it. Returns (content, extension)."""
    content = await validate_image_upload(file, max_size_mb=max_size_mb)
    content, ext, _content_type = compress_image(content)
    return content, ext


def save_file(
    bucket: str,
    filename: str,
    content: bytes,
    *,
    media_root: str,
    base_url: str,
    min_free_disk_mb: int,
) -> str:
    """Write content to disk and return its public URL.

    Raises HTTPException(507) if free disk space would drop below the floor —
    a single global guard against an upload spree filling the VPS disk.
    """
    dest = _safe_dest(media_root, bucket, filename)

    free_mb = shutil.disk_usage(media_root).free / (1024 * 1024)
    if free_mb < min_free_disk_mb:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="Server storage is full. Please try again later.",
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)

    return f"{base_url.rstrip('/')}/media/{bucket}/{filename}"


def delete_file(bucket: str, filename: str, *, media_root: str) -> None:
    """Remove a stored file. Silently ignores a missing file."""
    dest = _safe_dest(media_root, bucket, filename)
    dest.unlink(missing_ok=True)
