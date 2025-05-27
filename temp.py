import os
from googleapiclient.discovery import build

import dotenv

dotenv.load_dotenv()

GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

service = build("books", "v1", developerKey=GOOGLE_BOOKS_API_KEY)


def get_physical_isbn(ebook_isbn):
    try:
        response = service.volumes().list(q=f"isbn:{ebook_isbn}").execute()
        items = response.get("items", [])
        if not items:
            return None  # No book found for the ISBN

        volume_info = items[0]["volumeInfo"]
        identifiers = volume_info.get("industryIdentifiers", [])
        print(f"Book Identifiers: {identifiers=}")
        print_type = volume_info.get("printType", "UNKNOWN")

        # Look for physical book ISBN (assuming eBook ISBN was provided)
        for identifier in identifiers:
            if identifier["type"] in ["ISBN_10", "ISBN_13"] and print_type == "BOOK":
                # Verify if this is a physical book ISBN (not guaranteed)
                return identifier["identifier"]

        # If no physical book ISBN found or printType indicates eBook-only
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


# Example: eBook ISBN (replace with a known eBook ISBN)
ebook_isbn = "9781040010563"  # Example eBook ISBN
physical_isbn = get_physical_isbn(ebook_isbn)
print(f"Physical ISBN: {physical_isbn if physical_isbn else 'No physical book found'}")
