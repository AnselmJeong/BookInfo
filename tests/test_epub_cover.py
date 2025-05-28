import os
import io
import pytest
from bookinfo.core import extract_cover_image_epub
from PIL import Image

# Paths to test EPUB files (update these paths or add test files as needed)
EPUB_WITH_COVER = os.path.join(os.path.dirname(__file__), "sample_with_cover.epub")
EPUB_NO_COVER = os.path.join(os.path.dirname(__file__), "sample_no_cover.epub")


@pytest.mark.skipif(not os.path.exists(EPUB_WITH_COVER), reason="sample_with_cover.epub not found")
def test_extract_cover_image_epub_returns_bytes():
    cover_bytes = extract_cover_image_epub(EPUB_WITH_COVER)
    assert cover_bytes is not None, "Should extract cover image bytes from EPUB with cover"
    # Try to open as image
    image = Image.open(io.BytesIO(cover_bytes))
    image.verify()  # Will raise if not a valid image


@pytest.mark.skipif(not os.path.exists(EPUB_NO_COVER), reason="sample_no_cover.epub not found")
def test_extract_cover_image_epub_returns_none_for_no_cover():
    cover_bytes = extract_cover_image_epub(EPUB_NO_COVER)
    assert cover_bytes is None, "Should return None for EPUB with no cover image"
