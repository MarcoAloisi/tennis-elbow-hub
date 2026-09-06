"""Tests for local_storage: the Supabase-storage replacement writing to disk."""

import shutil

import pytest
from fastapi import HTTPException

from app.services.local_storage import UnsafePathError, delete_file, save_file


def test_save_file_writes_content_and_returns_public_url(tmp_path):
    url = save_file(
        "outfits",
        "abc123.webp",
        b"fake-image-bytes",
        media_root=str(tmp_path),
        base_url="https://api.tenniselbowhub.live",
        min_free_disk_mb=1,
    )

    assert url == "https://api.tenniselbowhub.live/media/outfits/abc123.webp"
    assert (tmp_path / "outfits" / "abc123.webp").read_bytes() == b"fake-image-bytes"


def test_save_file_creates_nested_directories_for_avatar_style_paths(tmp_path):
    save_file(
        "avatars",
        "user-42/avatar.webp",
        b"avatar-bytes",
        media_root=str(tmp_path),
        base_url="https://api.tenniselbowhub.live",
        min_free_disk_mb=1,
    )

    assert (tmp_path / "avatars" / "user-42" / "avatar.webp").read_bytes() == b"avatar-bytes"


@pytest.mark.parametrize("bad_filename", ["../../etc/passwd", "/etc/passwd", "a/../../b.webp"])
def test_save_file_rejects_path_traversal(tmp_path, bad_filename):
    with pytest.raises(UnsafePathError):
        save_file(
            "outfits",
            bad_filename,
            b"x",
            media_root=str(tmp_path),
            base_url="https://api.tenniselbowhub.live",
            min_free_disk_mb=1,
        )
    # nothing should have been written outside media_root
    assert list(tmp_path.rglob("*")) == []


def test_save_file_raises_507_when_disk_nearly_full(tmp_path, monkeypatch):
    monkeypatch.setattr(
        shutil,
        "disk_usage",
        lambda _path: shutil._ntuple_diskusage(total=10_000_000_000, used=9_999_000_000, free=1_000_000),
    )

    with pytest.raises(HTTPException) as exc_info:
        save_file(
            "outfits",
            "abc.webp",
            b"x",
            media_root=str(tmp_path),
            base_url="https://api.tenniselbowhub.live",
            min_free_disk_mb=500,
        )
    assert exc_info.value.status_code == 507


def test_delete_file_removes_existing_file(tmp_path):
    (tmp_path / "outfits").mkdir()
    (tmp_path / "outfits" / "abc.webp").write_bytes(b"x")

    delete_file("outfits", "abc.webp", media_root=str(tmp_path))

    assert not (tmp_path / "outfits" / "abc.webp").exists()


def test_delete_file_is_silent_when_file_missing(tmp_path):
    delete_file("outfits", "does-not-exist.webp", media_root=str(tmp_path))  # must not raise


def test_delete_file_rejects_path_traversal(tmp_path):
    with pytest.raises(UnsafePathError):
        delete_file("outfits", "../../etc/passwd", media_root=str(tmp_path))


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        test_save_file_writes_content_and_returns_public_url(Path(d))
    print("local_storage self-check passed")
