"""Simple PyQt5 window with an image folder picker and file list."""
import sys
from typing import List

from PyQt5 import QtWidgets

from image_search_app.scripts.search_for_img_file import choose_image_files


class SearchWindow(QtWidgets.QWidget):
    """Window that lets users pick a folder and view discovered images."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image Search")
        self.resize(500, 400)
        self.image_files: List[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.search_button = QtWidgets.QPushButton("Select Image Folder")
        self.search_button.clicked.connect(self._on_search_clicked)
        layout.addWidget(self.search_button)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        layout.addWidget(self.list_widget, 1)

    def _on_search_clicked(self) -> None:
        files = choose_image_files(parent=self)
        if files is None:
            return
        self.image_files = files
        self.list_widget.clear()
        if files:
            self.list_widget.addItems(files)
        else:
            self.list_widget.addItem("No images found in the selected folder.")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = SearchWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
