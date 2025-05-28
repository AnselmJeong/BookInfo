import flet as ft


def main(page: ft.Page):
    def on_result(e: ft.FilePickerResultEvent):
        print("Directory selected:", e.path)

    file_picker = ft.FilePicker(on_result=on_result)
    page.overlay.append(file_picker)
    page.update()
    page.add(
        ft.ElevatedButton(
            "Select Directory",
            on_click=lambda _: file_picker.get_directory_path(dialog_title="Select a directory"),
        )
    )


ft.app(target=main)
