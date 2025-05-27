import argparse
import os
from pathlib import Path
from bookinfo import get_book_info


def build_new_filename(info, original_ext):
    isbn = info.get("isbn_10") or "Unknown"
    title = info.get("title") or "Unknown"
    subtitle = info.get("subtitle")
    authors = info.get("authors_or_editors") or ["Unknown"]
    author = authors[0] if isinstance(authors, list) and authors else "Unknown"
    # Format: ISBN-10 - Title; Subtitle - First Author name.(ext)
    if subtitle:
        name = f"{isbn} - {title}; {subtitle} - {author}{original_ext}"
    else:
        name = f"{isbn} - {title} - {author}{original_ext}"
    # Remove forbidden characters for filenames
    return "".join(c for c in name if c not in '\\/:*?"<>|').strip()


def main():
    parser = argparse.ArgumentParser(description="Rename all PDF/EPUB books in a directory using bookinfo metadata.")
    parser.add_argument("directory", help="Directory containing PDF/EPUB files.")
    parser.add_argument(
        "--api-key", help="Google Books API key. If not provided, will use GOOGLE_BOOKS_API_KEY from environment."
    )
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("GOOGLE_BOOKS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Google Books API key must be provided via --api-key or the GOOGLE_BOOKS_API_KEY environment variable."
        )

    dir_path = Path(args.directory)
    for file_path in dir_path.iterdir():
        if file_path.suffix.lower() in [".pdf", ".epub"]:
            print(f"Processing: {file_path.name}")
            info = get_book_info(str(file_path), api_key)
            new_name = build_new_filename(info, file_path.suffix)
            new_path = file_path.with_name(new_name)
            if new_path != file_path:
                print(f"Renaming to: {new_name}")
                file_path.rename(new_path)
            else:
                print("No change needed.")


if __name__ == "__main__":
    main()
