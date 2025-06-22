import flet as ft
from pathlib import Path
import os
import io
from PIL import Image
from core import (
    get_books_info_list,
    extract_cover_image_epub,
    extract_first_page_image_pdf,
)

from dotenv import load_dotenv

# --- Ensure assets directory exists ---
ASSETS_DIR = Path(__file__).parent / "assets"

THUMBNAIL_DIR = Path("/Users/anselm/.BookInfo/assets")
THUMBNAIL_DIR.mkdir(exist_ok=True)

load_dotenv()
API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")


# Helper function to extract first page image and save to a temporary file
def extract_first_page_image(file_path_str: str) -> str | None:
    """
    Extracts the first page/cover image from a PDF or EPUB file.
    Saves it as a PNG file in the assets directory and returns the path to this file.
    Returns None if extraction fails or file type is unsupported.
    """
    try:
        file_path = Path(file_path_str)
        ext = file_path.suffix.lower()
        pil_image = None

        if ext == ".pdf":
            pil_image = extract_first_page_image_pdf(file_path_str)
        elif ext == ".epub":
            image_bytes = extract_cover_image_epub(file_path_str)
            if image_bytes:
                pil_image = Image.open(io.BytesIO(image_bytes))

        if pil_image:
            # Convert to RGBA if it has a palette (P mode) to ensure PNG saving works well
            if pil_image.mode == "P":
                pil_image = pil_image.convert("RGBA")
            elif pil_image.mode == "CMYK":  # common for PDFs
                pil_image = pil_image.convert("RGB")

            # Save to assets directory with a unique name
            image_filename = f"{file_path.stem}_page1.png"
            image_path = THUMBNAIL_DIR / image_filename
            pil_image.save(image_path, "PNG")
            return str(image_path)
    except Exception as e:
        print(f"Error extracting first page image for {file_path_str}: {e}")
    return None


# Helper function to build the new filename
def build_new_filename_from_info(info: dict, original_extension: str) -> str:
    """Builds the new filename based on book info and original extension."""
    isbn10 = info.get("isbn_10")
    title = info.get("title") or "UnknownTitle"
    subtitle = info.get("subtitle", "")  # Subtitle is optional
    authors_list = info.get("authors_or_editors")

    first_author = "UnknownAuthor"
    if authors_list and isinstance(authors_list, list) and len(authors_list) > 0:
        first_author = authors_list[0]

    filename_parts = []
    if isbn10:
        filename_parts.append(isbn10)
    if subtitle:
        title = f"{title}; {subtitle}"
    filename_parts.extend([title, first_author])

    base_name = " - ".join(filename_parts)
    base_name = f"{base_name}{original_extension}"

    # Sanitize filename (remove characters not allowed in macOS filenames)
    invalid_chars = '\\/:*?"<>|'
    sanitized_name = "".join(c for c in base_name if c not in invalid_chars)
    return sanitized_name.strip()


def main(page: ft.Page):
    page.title = "Book Renamer GUI"
    page.window.width = 1000
    page.window.height = 800
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START

    # --- FilePicker Setup (per Flet docs) ---
    def on_directory_result(e: ft.FilePickerResultEvent):
        nonlocal current_files_in_dir, current_file_processing_index
        if e.path:
            selected_directory_text.value = f"Selected: {e.path}"
            current_dir = Path(e.path)
            current_files_in_dir = sorted(
                [
                    f
                    for f in current_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in [".pdf", ".epub"]
                ]
            )
            # Reverse the order to process from bottom to top
            current_files_in_dir = list(reversed(current_files_in_dir))

            file_list_view.controls.clear()
            if current_files_in_dir:
                for f_path in reversed(current_files_in_dir):
                    file_list_view.controls.append(ft.Text(f_path.name))
                current_file_processing_index = 0
                process_file(current_files_in_dir[current_file_processing_index])
            else:
                file_list_view.controls.append(ft.Text("No PDF or EPUB files found."))
                processing_filename_text.value = "No files to process."
                candidate_cards_column.controls.clear()
        else:
            selected_directory_text.value = "Directory selection cancelled."
        page.update()

    # Create FilePicker and append to overlay at the top of main()
    file_picker = ft.FilePicker(on_result=on_directory_result)
    page.overlay.append(file_picker)
    page.update()  # Ensure overlay is registered before any button click

    # --- Application State ---
    current_files_in_dir = []
    current_file_processing_index = 0

    # --- UI Elements ---
    # Left Column
    selected_directory_text = ft.Text("No directory selected.")
    file_list_view = ft.ListView(
        expand=1, spacing=5, auto_scroll=True, item_extent=300, divider_thickness=1
    )

    # Right Column
    processing_filename_text = ft.Text(
        "Processing: (no file)", weight=ft.FontWeight.BOLD
    )
    candidate_cards_column = ft.Column(
        controls=[ft.Text("Select a directory and a file to see candidates.")],
        spacing=10,
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
    )

    temp_image_paths = []  # To store paths of temporary images for cleanup

    # --- Event Handlers ---
    def cleanup_temp_images():
        nonlocal temp_image_paths
        for temp_path_str in temp_image_paths:
            try:
                if temp_path_str and Path(temp_path_str).exists():
                    os.remove(temp_path_str)
            except Exception as e:
                print(f"Error deleting temp image {temp_path_str}: {e}")
        temp_image_paths = []

    def remove_file_from_list(filename: str):
        # Remove the bottom-most occurrence of the filename in the reversed display list
        for i in range(len(file_list_view.controls) - 1, -1, -1):
            if file_list_view.controls[i].value == filename:
                del file_list_view.controls[i]
                break
        file_list_view.update()

    def process_file(file_path: Path):
        nonlocal current_file_processing_index, temp_image_paths
        cleanup_temp_images()  # Clean up images from previous file

        # Highlight the current file at the bottom of the list
        display_index = len(file_list_view.controls) - 1 - current_file_processing_index
        for i, item in enumerate(file_list_view.controls):
            if i == display_index:
                file_list_view.controls[i] = ft.Text(
                    file_path.name, color=ft.Colors.BLUE, weight=ft.FontWeight.BOLD
                )
            else:
                file_list_view.controls[i] = ft.Text(item.value, size=12)
        file_list_view.update()

        # Abbreviate long file names for display
        max_len = 60
        name = file_path.name
        if len(name) > max_len:
            stem, ext = os.path.splitext(name)
            keep = max_len - len(ext) - 3  # 3 for '...'
            if keep > 0:
                name = stem[:keep] + "..." + ext
            else:
                name = "..." + ext
        processing_filename_text.value = f"Processing: {name}"
        candidate_cards_column.controls.clear()
        candidate_cards_column.controls.append(ft.ProgressBar())  # Show loading
        page.update()

        try:
            book_candidates = get_books_info_list(str(file_path), api_key=API_KEY)
        except Exception as e:
            print(f"Error fetching book info for {file_path.name}: {e}")
            book_candidates = []

        candidate_cards_column.controls.clear()  # Remove progress bar

        if not book_candidates:
            candidate_cards_column.controls.append(
                ft.Text(f"No candidates found for {file_path.name}.")
            )
        else:
            for i, candidate_info in enumerate(
                book_candidates[:3]
            ):  # Display up to 3 candidates
                google_thumbnail_url = candidate_info.get("cover_image_url")

                google_image_widget = ft.Image(
                    src=google_thumbnail_url
                    if google_thumbnail_url
                    else ASSETS_DIR / "No-image.png",
                    width=100,
                    height=150,
                    fit=ft.ImageFit.FILL,
                    # error_content=ft.Text("?", size=30),
                )

                first_page_image_path = extract_first_page_image(str(file_path))
                if first_page_image_path:
                    temp_image_paths.append(first_page_image_path)

                # Use /assets/filename.png for Flet static serving
                if first_page_image_path and os.path.exists(first_page_image_path):
                    image_filename = Path(first_page_image_path).name
                    image_src = THUMBNAIL_DIR / image_filename
                else:
                    image_src = ASSETS_DIR / "No-image.png"

                first_page_widget = ft.Image(
                    src=image_src,
                    width=100,
                    height=150,
                    fit=ft.ImageFit.FILL,
                    # error_content=ft.Text("?", size=30),
                )

                # Defensive extraction of fields with fallbacks
                isbn_10 = candidate_info.get("isbn_10")
                if not isinstance(isbn_10, str) or not isbn_10.strip():
                    isbn_10 = "N/A"

                title = candidate_info.get("title")
                if not isinstance(title, str) or not title.strip():
                    title = "N/A"

                subtitle = candidate_info.get("subtitle")
                if not isinstance(subtitle, str):
                    subtitle = ""

                authors = candidate_info.get("authors_or_editors")
                if not isinstance(authors, list) or not authors:
                    authors = ["N/A"]
                authors_str = ", ".join(authors)

                year = candidate_info.get("year_of_publication")
                if not isinstance(year, str) or not year.strip():
                    year = "N/A"

                info_column = ft.Column(
                    [
                        ft.Text(f"ISBN: {isbn_10}"),
                        ft.Text(f"Title: {title}", weight=ft.FontWeight.BOLD),
                        ft.Text(f"Subtitle: {subtitle}"),
                        ft.Text(f"Author(s): {authors_str}"),
                        ft.Text(f"Year: {year}"),
                    ],
                    spacing=3,
                    height=150,  # Adjust as needed, less than card_content height (220) minus button height
                    scroll=ft.ScrollMode.ADAPTIVE,
                )

                # Define on_select_candidate here before it's used in the lambda
                def on_select_candidate(e, selected_info, current_file):
                    new_filename_str = build_new_filename_from_info(
                        selected_info, current_file.suffix
                    )
                    new_file_path = current_file.with_name(new_filename_str)
                    try:
                        current_file.rename(new_file_path)
                        remove_file_from_list(current_file.name)
                        del current_files_in_dir[current_file_processing_index]
                    except Exception as ex:
                        print(f"Error renaming file: {ex}")
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"Error renaming: {ex}"), open=True
                        )

                    if current_file_processing_index < len(current_files_in_dir):
                        process_file(
                            current_files_in_dir[current_file_processing_index]
                        )
                    else:
                        processing_filename_text.value = "All files processed."
                        candidate_cards_column.controls.clear()
                        candidate_cards_column.controls.append(ft.Text("Done!"))
                        cleanup_temp_images()
                    page.update()

                select_button = ft.ElevatedButton(
                    "Select",
                    on_click=lambda e,
                    info=candidate_info,
                    fp=file_path: on_select_candidate(e, info, fp),
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    width=180,
                )

                # This column will hold the scrollable info_column and the button below it
                right_side_of_card = ft.Column(
                    [
                        info_column,  # Now info_column itself is scrollable
                        ft.Row(
                            [select_button],
                            spacing=10,
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ],
                    expand=True,
                    spacing=10,
                )

                card_content = ft.Container(
                    content=ft.Row(
                        [
                            ft.Row(  # Row for image columns
                                [
                                    ft.Column(
                                        [
                                            google_image_widget,
                                            ft.Text(
                                                "Image from Google",
                                                size=10,
                                                color="gray",
                                            ),
                                        ],
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    ft.Column(
                                        [
                                            first_page_widget,
                                            ft.Text(
                                                "Image from File", size=10, color="gray"
                                            ),
                                        ],
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                ],
                                spacing=5,
                            ),
                            ft.VerticalDivider(),
                            right_side_of_card,
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    padding=10,
                    height=220,
                )
                candidate_cards_column.controls.append(
                    ft.Card(
                        content=card_content,
                        elevation=2,
                        margin=ft.margin.symmetric(vertical=5),
                    )
                )

        # After all cards, add the skip button at the end if there were candidates
        if book_candidates:
            skip_button = ft.ElevatedButton(
                "Cancel (Skip File)",
                on_click=on_cancel_file,
                bgcolor=ft.Colors.ORANGE,
                color=ft.Colors.WHITE,
            )
            candidate_cards_column.controls.append(
                ft.Row(
                    [skip_button],
                    alignment=ft.MainAxisAlignment.END,
                )
            )
        page.update()

    def on_cancel_file(e):
        nonlocal current_file_processing_index
        if 0 <= current_file_processing_index < len(current_files_in_dir):
            remove_file_from_list(
                current_files_in_dir[current_file_processing_index].name
            )
            del current_files_in_dir[current_file_processing_index]
        if current_file_processing_index < len(current_files_in_dir):
            process_file(current_files_in_dir[current_file_processing_index])
        else:
            processing_filename_text.value = "All files processed."
            candidate_cards_column.controls.clear()
            candidate_cards_column.controls.append(ft.Text("Done!"))
            cleanup_temp_images()
        page.update()

    select_dir_button = ft.ElevatedButton(
        "Select Directory",
        icon=ft.Icons.FOLDER_OPEN,
        on_click=lambda _: file_picker.get_directory_path(
            dialog_title="Select Book Directory",
            initial_directory="/Volumes/Aquatope/Downloads/",
        ),
    )

    # --- Layout ---
    left_panel = ft.Column(
        [
            select_dir_button,
            selected_directory_text,
            ft.Text("Files in directory:", weight=ft.FontWeight.BOLD),
            ft.Container(
                content=file_list_view,
                border=ft.border.all(1, ft.Colors.OUTLINE),
                border_radius=5,
                padding=10,
                expand=True,  # Fill available vertical space
                height=page.window.height - 150
                if page.window.height
                else 600,  # Adjust height
            ),
        ],
        width=350,
        spacing=10,
    )

    right_panel = ft.Column(
        [
            # ft.Text(
            #     f"API Key: {API_KEY}",
            #     weight=ft.FontWeight.BOLD,
            # ),
            processing_filename_text,
            candidate_cards_column,
        ],
        expand=True,
        spacing=10,
    )

    page.add(
        ft.Row(
            [left_panel, ft.VerticalDivider(), right_panel],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
    )
    page.update()


ft.app(target=main)
