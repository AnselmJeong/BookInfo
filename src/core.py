import os

# import json
import logging
from typing import Optional, Dict, Any, List
from utils import (
    extract_isbns,
    clean_title_from_filename,
    is_pdf,
    is_epub,
    validate_file_path,
    validate_api_key,
)
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# import requests
from PIL import Image

# import io
# PDF/EPUB imports
import pypdf
import pdfplumber
from ebooklib import epub
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bookinfo")

logging.getLogger("pypdf").setLevel(logging.ERROR)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)

api_key = os.getenv("GOOGLE_BOOKS_API_KEY")

OUTPUT_FIELDS = [
    "isbn_10",
    "isbn_13",
    "title",
    "subtitle",
    "authors_or_editors",
    "year_of_publication",
    "source",
]


def default_output(source: str) -> Dict[str, Any]:
    return {
        "isbn_10": None,
        "isbn_13": None,
        "title": None,
        "subtitle": None,
        "authors_or_editors": None,
        "year_of_publication": None,
        "source": source,
    }


def extract_metadata_from_pdf(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            info = reader.metadata
            meta = {}
            if info:
                meta["title"] = info.title if info.title else None
                meta["author"] = info.author if info.author else None
            return meta
    except Exception as e:
        logger.warning(f"Failed to extract PDF metadata: {e}")
        return {}


def extract_metadata_from_epub(file_path: str) -> Dict[str, Any]:
    try:
        book = epub.read_epub(file_path)
        meta = {}
        # ISBN
        identifiers = book.get_metadata("DC", "identifier")
        for id_tuple in identifiers:
            val = id_tuple[0]
            if val and (len(val) == 10 or len(val) == 13):
                meta["isbn"] = val
        # Title
        titles = book.get_metadata("DC", "title")
        if titles:
            meta["title"] = titles[0][0]
        # Author
        creators = book.get_metadata("DC", "creator")
        if creators:
            meta["author"] = creators[0][0]
        return meta
    except Exception as e:
        logger.warning(f"Failed to extract EPUB metadata: {e}")
        return {}


def extract_text_from_pdf(file_path: str, max_pages: int = 5) -> str:
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= max_pages:
                    break
                text += page.extract_text() or ""
    except Exception as e:
        logger.warning(f"Failed to extract text from PDF: {e}")
    return text


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10))
def query_google_books_api(
    query: str, api_key: str = api_key
) -> Optional[List[Dict[str, Any]]]:
    try:
        service = build("books", "v1", developerKey=api_key)
        request = service.volumes().list(q=query, maxResults=5)
        response = request.execute()
        items = response.get("items", [])
        return items
    except HttpError as e:
        logger.error(f"Google Books API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error querying Google Books API: {e}")
        return None


def parse_google_books_item(item: Dict[str, Any]) -> Dict[str, Any]:
    volume = item.get("volumeInfo", {})
    industry_ids = volume.get("industryIdentifiers", [])
    isbn_10 = isbn_13 = None
    for id_obj in industry_ids:
        if id_obj.get("type") == "ISBN_10":
            isbn_10 = id_obj.get("identifier")
        elif id_obj.get("type") == "ISBN_13":
            isbn_13 = id_obj.get("identifier")
    image_links = volume.get("imageLinks", {})
    cover_image_url = (
        image_links.get("large")
        or image_links.get("thumbnail")
        or image_links.get("smallThumbnail")
    )
    return {
        "isbn_10": isbn_10,
        "isbn_13": isbn_13,
        "title": volume.get("title"),
        "subtitle": volume.get("subtitle"),
        "authors_or_editors": volume.get("authors"),
        "year_of_publication": str(volume.get("publishedDate"))[:4]
        if volume.get("publishedDate")
        else None,
        "cover_image_url": cover_image_url,
    }


def get_books_info_list(file_path: str, api_key: str = api_key) -> List[Dict[str, Any]]:
    """
    Returns a list of up to 10 matching book info dicts if ISBN is found, otherwise a single best match as before.
    """
    if not validate_file_path(file_path):
        logger.error(f"Invalid file path or unsupported file type: {file_path}")
        return [default_output(source="invalid_file")]
    if not validate_api_key(api_key):
        logger.error("Invalid or missing Google Books API key.")
        return [default_output(source="invalid_api_key")]

    filename = os.path.basename(file_path)
    isbn10s, isbn13s = extract_isbns(filename)
    if isbn13s or isbn10s:
        isbn = isbn13s[0] if isbn13s else isbn10s[0]
        logger.info(f"Found ISBN in filename: {isbn}")
        items = query_google_books_api(f"isbn:{isbn}", api_key)
        if items:
            results = []
            for item in items[:10]:
                result = parse_google_books_item(item)
                result["source"] = "isbn_filename"
                results.append(result)
            return results
        else:
            return [default_output(source="isbn_filename")]

    meta = {}
    if is_pdf(file_path):
        meta = extract_metadata_from_pdf(file_path)
    elif is_epub(file_path):
        meta = extract_metadata_from_epub(file_path)
    meta_text = " ".join(str(v) for v in meta.values() if v)
    isbn10s, isbn13s = extract_isbns(meta_text)
    if isbn13s or isbn10s:
        isbn = isbn13s[0] if isbn13s else isbn10s[0]
        logger.info(f"Found ISBN in file metadata: {isbn}")
        items = query_google_books_api(f"isbn:{isbn}", api_key)
        if items:
            results = []
            for item in items[:10]:
                result = parse_google_books_item(item)
                result["source"] = "file_metadata"
                results.append(result)
            return results
        else:
            return [default_output(source="file_metadata")]
    if meta.get("title"):
        query = meta["title"]
        if meta.get("author"):
            query += f" {meta['author']}"
        logger.info(f"Searching Google Books API with metadata title/author: {query}")
        items = query_google_books_api(query, api_key)
        if items:
            result = parse_google_books_item(items[0])
            result["source"] = "file_metadata"
            return [result]
        else:
            return [default_output(source="file_metadata")]

    title = clean_title_from_filename(filename)
    if title:
        logger.info(f"Using cleaned filename as title: {title}")
        items = query_google_books_api(title, api_key)
        if items:
            result = parse_google_books_item(items[0])
            result["source"] = "filename_title"
            return [result]
        else:
            return [default_output(source="filename_title")]

    if is_pdf(file_path):
        text = extract_text_from_pdf(file_path)
        isbn10s, isbn13s = extract_isbns(text)
        if isbn13s or isbn10s:
            isbn = isbn13s[0] if isbn13s else isbn10s[0]
            logger.info(f"Found ISBN in PDF text: {isbn}")
            items = query_google_books_api(f"isbn:{isbn}", api_key)
            if items:
                results = []
                for item in items[:10]:
                    result = parse_google_books_item(item)
                    result["source"] = "pdf_text"
                    results.append(result)
                return results
            else:
                return [default_output(source="pdf_text")]
        lines = text.splitlines()
        for line in lines[:20]:
            if len(line.strip()) > 5 and not any(c.isdigit() for c in line):
                logger.info(f"Trying line as title from PDF text: {line.strip()}")
                items = query_google_books_api(line.strip(), api_key)
                if items:
                    result = parse_google_books_item(items[0])
                    result["source"] = "pdf_text"
                    return [result]
        return [default_output(source="pdf_text")]

    logger.info("No metadata found for file.")
    return [default_output(source="not_found")]


def get_google_books_image_url(query: str, api_key: str) -> Optional[str]:
    """
    Returns the thumbnail image URL from the first Google Books API result for the query.
    """
    items = query_google_books_api(query, api_key)
    if items:
        volume = items[0].get("volumeInfo", {})
        image_links = volume.get("imageLinks", {})
        # Prefer 'large' or 'thumbnail'
        return image_links.get("large") or image_links.get("thumbnail")
    return None


def extract_first_page_image_pdf(file_path: str) -> Optional[Image.Image]:
    """
    Returns a PIL Image of the first page of a PDF file.
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            if pdf.pages:
                page = pdf.pages[0]
                # Render as image (requires pdfplumber[image] and Pillow)
                return page.to_image(resolution=200).original
    except Exception as e:
        logger.warning(f"Failed to extract first page image from PDF: {e}")
    return None


def extract_cover_image_epub(epub_path: str) -> bytes | None:
    """
    Extracts the cover image from an EPUB file and returns it as bytes.
    Returns None if no cover image is found.
    """
    from ebooklib import epub

    book = epub.read_epub(epub_path)
    cover_id = None

    # Step 1: Try to find the cover id from the OPF metadata
    for meta, attrs in book.get_metadata("OPF", "cover"):
        if attrs.get("name") == "cover" and "content" in attrs:
            cover_id = attrs["content"]
            break

    # Step 2: If cover_id found, get the corresponding item
    if cover_id:
        item = book.get_item_with_id(cover_id)
        if item:
            return item.get_content()
    else:
        # Fallback: Try to find the first image in the manifest
        import ebooklib

        for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
            return item.get_content()

    return None
