import os
import tempfile
import pytest
from bookinfo import utils


def test_extract_isbns():
    text = "This is a test with ISBN 9781234567890 and 123456789X."
    isbn10s, isbn13s = utils.extract_isbns(text)
    assert "123456789X" in isbn10s
    assert "9781234567890" in isbn13s

    # Test with dashes
    text2 = "ISBN 978-1-2345-6789-0 and 1-23456789-X"
    isbn10s, isbn13s = utils.extract_isbns(text2)
    assert "123456789X" in isbn10s
    assert "9781234567890" in isbn13s

    # Test with spaces
    text3 = "ISBN 978 1 2345 6789 0 and 1 23456789 X"
    isbn10s, isbn13s = utils.extract_isbns(text3)
    assert "123456789X" in isbn10s
    assert "9781234567890" in isbn13s


def test_clean_title_from_filename():
    filename = "9781234567890_The_Great_Book-2021.pdf"
    title = utils.clean_title_from_filename(filename)
    assert title == "The Great Book 2021"


def test_is_pdf_and_is_epub():
    assert utils.is_pdf("file.pdf")
    assert not utils.is_pdf("file.epub")
    assert utils.is_epub("file.epub")
    assert not utils.is_epub("file.pdf")


def test_validate_file_path():
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        assert utils.validate_file_path(tmp.name)
    with tempfile.NamedTemporaryFile(suffix=".epub") as tmp:
        assert utils.validate_file_path(tmp.name)
    assert not utils.validate_file_path("/nonexistent/file.pdf")
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        assert not utils.validate_file_path(tmp.name)


def test_validate_api_key():
    assert utils.validate_api_key("abc123")
    assert not utils.validate_api_key("")
    assert not utils.validate_api_key(None)
