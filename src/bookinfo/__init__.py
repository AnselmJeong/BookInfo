from .core import get_books_info_list


def get_book_info(file_path, api_key):
    """
    Backward-compatible wrapper: returns the first result from get_books_info_list.
    """
    results = get_books_info_list(file_path, api_key)
    return results[0] if results else None
