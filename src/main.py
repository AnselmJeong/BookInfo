import flet as ft
from pathlib import Path
import tempfile
import os
import io
from PIL import Image
import sys


# Ensure the bookinfo package in the current directory can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print(f"sys.path: {sys.path}")
try:
    import bookinfo
except ImportError:
    print("Error: The 'bookinfo' package was not found in the current directory.")
    print(
        "Please ensure 'main.py' (or your entry script) is in the 'src' directory and the 'bookinfo' package is in the project root."
    )
    sys.exit(1)


# Helper function to extract first page image and save to a temporary file
def extract_first_page_image(file_path_str: str) -> str | None:
    """
    Extracts the first page/cover image from a PDF or EPUB file.
    Saves it as a temporary PNG file and returns the path to this temp file.
    Returns None if extraction fails or file type is unsupported.
    """
    try:
        file_path = Path(file_path_str)
        ext = file_path.suffix.lower()
        pil_image = None

        if ext == ".pdf":
            pil_image = bookinfo.core.extract_first_page_image_pdf(file_path_str)
        elif ext == ".epub":
            image_bytes = bookinfo.core.extract_cover_image_epub(file_path_str)
            if image_bytes:
                pil_image = Image.open(io.BytesIO(image_bytes))

        if pil_image:
            # Convert to RGBA if it has a palette (P mode) to ensure PNG saving works well
            if pil_image.mode == "P":
                pil_image = pil_image.convert("RGBA")
            elif pil_image.mode == "CMYK":  # common for PDFs
                pil_image = pil_image.convert("RGB")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                pil_image.save(tmp_file.name, "PNG")
                return tmp_file.name
    except Exception as e:
        print(f"Error extracting first page image for {file_path_str}: {e}")
    return None


# Helper function to build the new filename
def build_new_filename_from_info(info: dict, original_extension: str) -> str:
    """Builds the new filename based on book info and original extension."""
    isbn10 = info.get("isbn_10") or "UnknownISBN"
    title = info.get("title") or "UnknownTitle"
    subtitle = info.get("subtitle", "")  # Subtitle is optional
    authors_list = info.get("authors_or_editors")

    first_author = "UnknownAuthor"
    if authors_list and isinstance(authors_list, list) and len(authors_list) > 0:
        first_author = authors_list[0]

    filename_parts = [isbn10, title]
    if subtitle:  # Only add subtitle if it exists
        filename_parts.append(f";{subtitle}")
    filename_parts.append(f" - {first_author}{original_extension}")

    base_name = " - ".join(filename_parts)

    # Sanitize filename (remove characters not allowed in macOS filenames)
    invalid_chars = '\\/:*?"<>|'
    sanitized_name = "".join(c for c in base_name if c not in invalid_chars)
    return sanitized_name.strip()


def main(page: ft.Page):
    page.title = "Book Renamer GUI"
    page.window_width = 1200
    page.window_height = 800
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START

    # --- FilePicker Setup (per Flet docs) ---
    def on_directory_result(e: ft.FilePickerResultEvent):
        nonlocal current_files_in_dir, current_file_processing_index
        if e.path:
            selected_directory_text.value = f"Selected: {e.path}"
            current_dir = Path(e.path)
            current_files_in_dir = sorted([
                f for f in current_dir.iterdir() if f.is_file() and f.suffix.lower() in [".pdf", ".epub"]
            ])

            file_list_view.controls.clear()
            if current_files_in_dir:
                for f_path in current_files_in_dir:
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

    # Attempt to get API key from environment
    # This key is used by bookinfo.get_books_info_list implicitly if not passed
    # or can be passed explicitly if your bookinfo functions require it.
    # For this example, we assume bookinfo.get_books_info_list can use an env var
    # or that the API key is passed as an argument to it.https://flet.dev/docs/cookbook/file-picker-and-uploads/
    # If GOOGLE_BOOKS_API_KEY is required by bookinfo, ensure it's set.
    # For now, we'll just try to load it, and bookinfo will handle if it's missing.
    api_key_env = os.getenv("GOOGLE_BOOKS_API_KEY")
    if not api_key_env:
        page.banner = ft.Banner(
            bgcolor=ft.Colors.AMBER_100,
            leading=ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER, size=40),
            content=ft.Text(
                "Warning: GOOGLE_BOOKS_API_KEY environment variable not set. Book info retrieval might fail."
            ),
            actions=[ft.TextButton("OK", on_click=lambda _: setattr(page.banner, "open", False) or page.update())],
        )
        page.banner.open = True

    # --- UI Elements ---
    # Left Column
    selected_directory_text = ft.Text("No directory selected.")
    file_list_view = ft.ListView(expand=1, spacing=5, auto_scroll=True)

    # Right Column
    processing_filename_text = ft.Text("Processing: (no file)", weight=ft.FontWeight.BOLD)
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

    def process_file(file_path: Path):
        nonlocal current_file_processing_index, temp_image_paths
        cleanup_temp_images()  # Clean up images from previous file

        processing_filename_text.value = f"Processing: {file_path.name}"
        candidate_cards_column.controls.clear()
        candidate_cards_column.controls.append(ft.ProgressBar())  # Show loading
        page.update()

        try:
            # bookinfo.get_books_info_list is expected to take api_key
            # If your bookinfo setup reads API_KEY from env, you might not need to pass it.
            # Adjust if your bookinfo package API is different.
            book_candidates = bookinfo.get_books_info_list(str(file_path), api_key=api_key_env)
        except Exception as e:
            print(f"Error fetching book info for {file_path.name}: {e}")
            book_candidates = []

        candidate_cards_column.controls.clear()  # Remove progress bar

        if not book_candidates:
            candidate_cards_column.controls.append(ft.Text(f"No candidates found for {file_path.name}."))
        else:
            for i, candidate_info in enumerate(book_candidates[:3]):  # Display up to 3 candidates
                google_thumbnail_url = candidate_info.get("cover_image_url")

                google_image_widget = ft.Image(
                    src=google_thumbnail_url
                    if google_thumbnail_url
                    else "https://via.placeholder.com/80x120.png?text=No+Cover",
                    width=80,
                    height=120,
                    fit=ft.ImageFit.CONTAIN,
                    error_content=ft.Text("?", size=30),
                )

                first_page_image_path = extract_first_page_image(str(file_path))
                if first_page_image_path:
                    temp_image_paths.append(first_page_image_path)

                first_page_widget = ft.Image(
                    src=f"file://{first_page_image_path}"
                    if first_page_image_path
                    else "https://via.placeholder.com/80x120.png?text=No+Page",
                    width=80,
                    height=120,
                    fit=ft.ImageFit.CONTAIN,
                    error_content=ft.Text("?", size=30),
                )

                info_column = ft.Column(
                    [
                        ft.Text(f"ISBN: {candidate_info.get('isbn_10', 'N/A')}"),
                        ft.Text(f"Title: {candidate_info.get('title', 'N/A')}", weight=ft.FontWeight.BOLD),
                        ft.Text(f"Subtitle: {candidate_info.get('subtitle', '')}"),
                        ft.Text(f"Author(s): {', '.join(candidate_info.get('authors_or_editors', ['N/A']))}"),
                    ],
                    spacing=3,
                )

                def on_select_candidate(e, selected_info=candidate_info, current_file=file_path):
                    new_filename_str = build_new_filename_from_info(selected_info, current_file.suffix)
                    new_file_path = current_file.with_name(new_filename_str)
                    try:
                        current_file.rename(new_file_path)
                        print(f"Renamed '{current_file.name}' to '{new_file_path.name}'")
                        # Update file list view
                        for i_list, item_text_widget in enumerate(file_list_view.controls):
                            if item_text_widget.value == current_file.name:
                                item_text_widget.value = new_file_path.name
                                current_files_in_dir[i_list] = new_file_path  # Update underlying list
                                break
                        file_list_view.update()
                    except Exception as ex:
                        print(f"Error renaming file: {ex}")
                        page.snack_bar = ft.SnackBar(ft.Text(f"Error renaming: {ex}"), open=True)

                    # Move to next file
                    nonlocal current_file_processing_index
                    current_file_processing_index += 1
                    if current_file_processing_index < len(current_files_in_dir):
                        process_file(current_files_in_dir[current_file_processing_index])
                    else:
                        processing_filename_text.value = "All files processed."
                        candidate_cards_column.controls.clear()
                        candidate_cards_column.controls.append(ft.Text("Done!"))
                        cleanup_temp_images()
                    page.update()

                select_button = ft.ElevatedButton(
                    "Select",
                    on_click=lambda e, info=candidate_info, fp=file_path: on_select_candidate(e, info, fp),
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                )

                card_content = ft.Row(
                    [
                        ft.Column([google_image_widget, first_page_widget], spacing=5),
                        ft.VerticalDivider(),
                        ft.Column([info_column, select_button], expand=True, spacing=10),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
                candidate_cards_column.controls.append(
                    ft.Card(content=card_content, elevation=2, margin=ft.margin.symmetric(vertical=5))
                )

        def on_cancel_file(e):
            nonlocal current_file_processing_index
            current_file_processing_index += 1
            if current_file_processing_index < len(current_files_in_dir):
                process_file(current_files_in_dir[current_file_processing_index])
            else:
                processing_filename_text.value = "All files processed."
                candidate_cards_column.controls.clear()
                candidate_cards_column.controls.append(ft.Text("Done!"))
                cleanup_temp_images()
            page.update()

        if book_candidates:  # Only add cancel button if there were candidates
            candidate_cards_column.controls.append(
                ft.ElevatedButton(
                    "Cancel (Skip File)", on_click=on_cancel_file, bgcolor=ft.Colors.ORANGE, color=ft.Colors.WHITE
                )
            )
        page.update()

    select_dir_button = ft.ElevatedButton(
        "Select Directory",
        icon=ft.Icons.FOLDER_OPEN,
        on_click=lambda _: file_picker.get_directory_path(dialog_title="Select Book Directory"),
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
                height=page.window_height - 150 if page.window_height else 600,  # Adjust height
            ),
        ],
        width=350,
        spacing=10,
    )

    right_panel = ft.Column(
        [
            processing_filename_text,
            candidate_cards_column,
        ],
        expand=True,
        spacing=10,
    )

    page.add(
        ft.Row(
            [left_panel, ft.VerticalDivider(), right_panel], expand=True, vertical_alignment=ft.CrossAxisAlignment.START
        )
    )
    page.update()


if __name__ == "__main__":
    ft.app(target=main)
