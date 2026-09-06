"""Self-check for compress_image: the egress-fix resize/re-encode step."""

from io import BytesIO

from PIL import Image

from app.core.security import MAX_IMAGE_DIMENSION, compress_image


def _png_bytes(size: tuple[int, int]) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color=(200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_oversized_png_is_downscaled_and_converted_to_webp():
    original = _png_bytes((3000, 2000))
    out_bytes, ext, content_type = compress_image(original)

    assert ext == "webp"
    assert content_type == "image/webp"
    assert len(out_bytes) < len(original)

    with Image.open(BytesIO(out_bytes)) as img:
        assert img.format == "WEBP"
        assert max(img.size) <= MAX_IMAGE_DIMENSION


def test_small_image_is_still_converted_but_not_upscaled():
    original = _png_bytes((400, 300))
    out_bytes, ext, _ = compress_image(original)

    assert ext == "webp"
    with Image.open(BytesIO(out_bytes)) as img:
        assert img.size == (400, 300)


def test_animated_gif_passes_through_unchanged():
    buf = BytesIO()
    frames = [Image.new("RGB", (100, 100), color=c) for c in [(255, 0, 0), (0, 255, 0)]]
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    original = buf.getvalue()

    out_bytes, ext, content_type = compress_image(original)

    assert out_bytes == original
    assert ext == "gif"
    assert content_type == "image/gif"


if __name__ == "__main__":
    test_oversized_png_is_downscaled_and_converted_to_webp()
    test_small_image_is_still_converted_but_not_upscaled()
    test_animated_gif_passes_through_unchanged()
    print("compress_image self-check passed")
