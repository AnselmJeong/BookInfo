import os
import tempfile
import pytest
from unittest.mock import patch
from bookinfo import core
import io
from PIL import Image


def test_default_output():
    out = core.default_output("test_source")
    assert out["source"] == "test_source"
    for k in [
        "isbn_10",
        "isbn_13",
        "title",
        "subtitle",
        "authors_or_editors",
        "year_of_publication",
    ]:
        assert out[k] is None


def test_parse_google_books_item():
    item = {
        "volumeInfo": {
            "title": "Test Book",
            "subtitle": "A Story",
            "authors": ["Author One", "Author Two"],
            "publishedDate": "2020-01-01",
            "industryIdentifiers": [
                {"type": "ISBN_10", "identifier": "1234567890"},
                {"type": "ISBN_13", "identifier": "9781234567890"},
            ],
        }
    }
    result = core.parse_google_books_item(item)
    assert result["isbn_10"] == "1234567890"
    assert result["isbn_13"] == "9781234567890"
    assert result["title"] == "Test Book"
    assert result["subtitle"] == "A Story"
    assert result["authors_or_editors"] == ["Author One", "Author Two"]
    assert result["year_of_publication"] == "2020"


@patch("bookinfo.core.validate_file_path", return_value=False)
def test_get_book_info_invalid_file(mock_validate):
    result = core.get_books_info_list("/nonexistent/file.pdf", api_key="abc")[0]
    assert result["source"] == "invalid_file"


@patch("bookinfo.core.validate_api_key", return_value=False)
def test_get_book_info_invalid_api_key(mock_validate):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        result = core.get_books_info_list(tmp.name, api_key="")[0]
        assert result["source"] == "invalid_api_key"


SAMPLE_PDF = os.path.join(os.path.dirname(__file__), "sample.pdf")


@pytest.mark.skipif(not os.path.exists(SAMPLE_PDF), reason="sample.pdf not found")
def test_extract_first_page_image_pdf_returns_image():
    from bookinfo.core import extract_first_page_image_pdf

    image = extract_first_page_image_pdf(SAMPLE_PDF)
    assert image is not None, "Should extract an image from the first page of the PDF"
    assert isinstance(image, Image.Image), "Returned object should be a PIL Image"
    # Optionally, check image size or format
