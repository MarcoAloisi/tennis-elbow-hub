"""Regex self-check for the one-off Supabase image migration script.

The migration's only real logic is spotting Supabase storage URLs (in plain
DB columns and inline inside Guide.content HTML) and pulling out
bucket/filename — everything else is a download-and-write loop trusted to
httpx/pathlib. This is the part worth a test.
"""

from scripts.migrate_supabase_images import SUPABASE_URL_RE


def test_matches_plain_column_url():
    url = "https://abcxyz.supabase.co/storage/v1/object/public/outfits/abc-123.webp"
    match = SUPABASE_URL_RE.search(url)
    assert match is not None
    assert match.group(1) == "outfits"
    assert match.group(2) == "abc-123.webp"


def test_matches_url_embedded_in_html():
    html = (
        '<p>intro</p><img src="https://abcxyz.supabase.co/storage/v1/object/public/'
        'guide-images/def-456.webp" alt=""><p>more text</p>'
    )
    match = SUPABASE_URL_RE.search(html)
    assert match is not None
    assert match.group(1) == "guide-images"
    assert match.group(2) == "def-456.webp"
    assert match.group(0).endswith("def-456.webp")


def test_matches_nested_avatar_path():
    url = "https://abcxyz.supabase.co/storage/v1/object/public/avatars/user-42/avatar.webp"
    match = SUPABASE_URL_RE.search(url)
    assert match is not None
    assert match.group(1) == "avatars"
    assert match.group(2) == "user-42/avatar.webp"


def test_does_not_match_non_supabase_url():
    assert SUPABASE_URL_RE.search("https://api.tenniselbowhub.live/media/outfits/x.webp") is None


if __name__ == "__main__":
    test_matches_plain_column_url()
    test_matches_url_embedded_in_html()
    test_matches_nested_avatar_path()
    test_does_not_match_non_supabase_url()
    print("migrate_supabase_images regex self-check passed")
