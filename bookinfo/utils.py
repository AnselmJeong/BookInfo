import re
from pathlib import Path
from typing import Optional, Tuple, List


# Accept ISBNs with or without dashes
def _normalize_isbn(isbn: str) -> str:
    return re.sub(r"[- ]", "", isbn).upper()


# More structurally explicit regexes
# ISBN-10: 9 digits (with optional separators), then a digit or X (with optional separator)
ISBN10_REGEX = re.compile(
    r"(?<!\d)"  # Not preceded by a digit
    r"\d[\- ]*"  # First digit, optional separator
    r"(?:\d[\- ]*){8}"  # 8x: digit, optional separator
    r"[\dXx]"  # Check digit (digit or X)
    r"(?!\d)",  # Not followed by a digit
    re.UNICODE,
)

# ISBN-13: 978/979, then 10 digits (with optional separators) OR 13 consecutive digits starting with 978/979
ISBN13_REGEX = re.compile(r"(?<!\d)(97[89](?:[\- ]*\d){10}|97[89]\d{10})(?!\d)", re.UNICODE)


def extract_isbns(text: str) -> Tuple[List[str], List[str]]:
    """
    Extract ISBN-10 and ISBN-13 numbers from a given text, allowing for dashes or spaces.
    Returns a tuple of (isbn10_list, isbn13_list), normalized (no dashes/spaces, uppercase X).
    """
    raw_isbn10s = ISBN10_REGEX.findall(text)
    raw_isbn13s = ISBN13_REGEX.findall(text)
    isbn10s = []
    isbn13s = []
    for raw in raw_isbn10s:
        norm = _normalize_isbn(raw)
        if len(norm) == 10:
            isbn10s.append(norm)
    for raw in raw_isbn13s:
        norm = _normalize_isbn(raw)
        if len(norm) == 13:
            isbn13s.append(norm)
    return isbn10s, isbn13s


def clean_title_from_filename(filename: str) -> str:
    """
    Clean the filename to extract a likely book title.
    Removes extension, underscores, dashes, and extra spaces.
    """
    path = Path(filename)
    name = path.stem
    # Remove all ISBN-13s (with or without dashes/spaces) from anywhere in the name
    name = ISBN13_REGEX.sub("", name)
    # Remove all ISBN-10s (with or without dashes/spaces) from anywhere in the name
    name = ISBN10_REGEX.sub("", name)
    # Remove any leftover leading/trailing separators or whitespace
    name = re.sub(r"[_\-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def is_pdf(file_path: str) -> bool:
    return Path(file_path).suffix.lower() == ".pdf"


def is_epub(file_path: str) -> bool:
    return Path(file_path).suffix.lower() == ".epub"


def validate_file_path(file_path: str) -> bool:
    path = Path(file_path)
    return path.is_file() and (is_pdf(file_path) or is_epub(file_path))


def validate_api_key(api_key: Optional[str]) -> bool:
    return bool(api_key and isinstance(api_key, str) and len(api_key) > 0)
