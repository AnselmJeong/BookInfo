# BookInfo

Extract book metadata from PDF or EPUB files using the Google Books API.

## Features
- Extracts ISBN-10, ISBN-13, title, subtitle, authors/editors, and year of publication
- Supports PDF and EPUB files
- Uses Google Books API for reliable metadata
- Heuristic extraction: filename, embedded metadata, and text
- Outputs results in JSON format
- Command-line interface (CLI) and Python API
- Handles API rate limits and errors gracefully

## Installation

```bash
pip install -r requirements.txt
python setup.py install
```

## Google Books API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the "Books API"
3. Create an API key and restrict it as needed
4. Use the API key with the package (see below)

## Usage

### Programmatic
```python
from bookinfo import get_book_info
result = get_book_info("path/to/book.pdf", api_key="your-api-key")
print(result)
```

### CLI
```bash
bookinfo path/to/book.epub --api-key your-api-key
```

## Output JSON Format
```json
{
  "isbn_10": "string or null",
  "isbn_13": "string or null",
  "title": "string or null",
  "subtitle": "string or null",
  "authors_or_editors": ["string", ...] or null,
  "year_of_publication": "string or null",
  "source": "isbn_filename | file_metadata | filename_title | pdf_text"
}
```

- The `source` field indicates which heuristic method was used.
- If no metadata is found, all fields except `source` will be `null`.

## Heuristic Extraction Steps
1. **ISBN in Filename**: Uses ISBN found in filename to query Google Books API.
2. **Metadata in File**: Extracts embedded metadata (ISBN, title, author) from PDF/EPUB.
3. **Filename as Title**: Uses cleaned filename as title to search Google Books API. If multiple matches, the top result is returned. (See note below.)
4. **Text Extraction from PDF**: Extracts text from first 5 pages of PDF to find ISBN or title/author.

**Note:** If multiple books are found in the filename title search, only the top result is returned. For advanced use, modify the code to access additional matches.

## API Documentation

### `get_book_info(file_path, api_key)`
- **file_path**: Path to PDF or EPUB file
- **api_key**: Google Books API key
- **Returns**: Dictionary with book metadata (see JSON format above)

## Error Handling
- Invalid files, missing metadata, and API errors are handled gracefully with meaningful messages and `null` fields in output.

## Testing

Run unit tests with:
```bash
pytest tests/
```

## License
MIT License
