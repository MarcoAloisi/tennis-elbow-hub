"""One-off: copy images out of Supabase Storage onto local disk, rewrite DB URLs.

Run once on the VPS after the code deploy that adds local_storage.py:

    .venv/bin/python -m scripts.migrate_supabase_images

Idempotent — skips anything that doesn't still point at supabase.co, so it's
safe to re-run if it fails partway through.
"""

import asyncio
import re

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.models.guide import Guide
from app.models.outfit import Outfit
from app.models.user_profile import UserProfile

SUPABASE_URL_RE = re.compile(r"https://[a-z0-9]+\.supabase\.co/storage/v1/object/public/([^/]+)/([^\s\"'<>]+)")


async def _download(client: httpx.AsyncClient, url: str) -> bytes:
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.content


def _write_local(media_root: str, bucket: str, filename: str, content: bytes) -> None:
    from pathlib import Path

    dest = Path(media_root) / bucket / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)


async def migrate_column(client, session, model, column_name, media_root, base_url):
    column = getattr(model, column_name)
    rows = (await session.execute(select(model).where(column.like("%supabase.co%")))).scalars().all()
    for row in rows:
        url = getattr(row, column_name)
        match = SUPABASE_URL_RE.search(url)
        if not match:
            print(f"  SKIP (unrecognized URL) {model.__name__}.{row.id}: {url}")
            continue
        bucket, filename = match.group(1), match.group(2)
        content = await _download(client, url)
        _write_local(media_root, bucket, filename, content)
        setattr(row, column_name, f"{base_url}/media/{bucket}/{filename}")
        print(f"  migrated {model.__name__}.{row.id}: {bucket}/{filename}")
    await session.commit()


async def migrate_guide_content(client, session, media_root, base_url):
    rows = (await session.execute(select(Guide).where(Guide.content.like("%supabase.co%")))).scalars().all()
    for row in rows:
        content_html = row.content
        for match in SUPABASE_URL_RE.finditer(content_html):
            full_url, bucket, filename = match.group(0), match.group(1), match.group(2)
            data = await _download(client, full_url)
            _write_local(media_root, bucket, filename, data)
            content_html = content_html.replace(full_url, f"{base_url}/media/{bucket}/{filename}")
            print(f"  migrated inline image in Guide.{row.id}: {bucket}/{filename}")
        row.content = content_html
    await session.commit()


async def main() -> None:
    settings = get_settings()
    session_factory = get_session_factory()
    base_url = settings.media_base_url.rstrip("/")

    async with httpx.AsyncClient(timeout=30.0) as client, session_factory() as session:
        print("Migrating Outfit.image_url ...")
        await migrate_column(client, session, Outfit, "image_url", settings.media_root, base_url)

        print("Migrating Guide.thumbnail_url ...")
        await migrate_column(client, session, Guide, "thumbnail_url", settings.media_root, base_url)

        print("Migrating UserProfile.avatar_url ...")
        await migrate_column(client, session, UserProfile, "avatar_url", settings.media_root, base_url)

        print("Migrating inline images in Guide.content ...")
        await migrate_guide_content(client, session, settings.media_root, base_url)

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
