import os
import tempfile
import pytest
from unittest.mock import patch
from bookinfo import core


def test_default_output():
    out = core.default_output("test_source")
    assert out["source"] == "test_source"
    for k in ["isbn_10", "isbn_13", "title", "subtitle", "authors_or_editors", "year_of_publication"]:
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
    result = core.get_book_info("/nonexistent/file.pdf", api_key="abc")
    assert result["source"] == "invalid_file"


@patch("bookinfo.core.validate_api_key", return_value=False)
def test_get_book_info_invalid_api_key(mock_validate):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        result = core.get_book_info(tmp.name, api_key="")
        assert result["source"] == "invalid_api_key"
