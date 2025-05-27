import argparse
import json
import sys
from .core import get_book_info


def main():
    parser = argparse.ArgumentParser(description="Extract book metadata from PDF or EPUB files using Google Books API.")
    parser.add_argument("file_path", help="Path to the PDF or EPUB file.")
    # parser.add_argument("--api-key", required=True, help="Google Books API key.")
    args = parser.parse_args()

    try:
        result = get_book_info(args.file_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
