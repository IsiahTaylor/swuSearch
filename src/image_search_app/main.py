"""Simple PyQt5 window with an image folder picker, card list, and preview."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import appdirs
from PyQt5 import QtCore, QtGui, QtWidgets

from image_search_app.scripts.batch_img_to_card import images_to_cards
from image_search_app.scripts.search_for_img_file import choose_image_folder


class SearchWindow(QtWidgets.QWidget):
    """Window that lets users pick a folder and view discovered images."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image Search")
        self.resize(900, 675)
        self.cards: List[Dict[str, object]] = []
        self._build_ui()
        self._load_cached_cards()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        controls = QtWidgets.QHBoxLayout()
        controls.setSpacing(8)
        layout.addLayout(controls)

        self.clear_button = QtWidgets.QPushButton("Clear Cache")
        self.clear_button.clicked.connect(self._on_clear_clicked)
        controls.addWidget(self.clear_button)

        self.search_button = QtWidgets.QPushButton("Scan Image Folder")
        self.search_button.clicked.connect(self._on_scan_clicked)
        controls.addWidget(self.search_button)

        content_row = QtWidgets.QHBoxLayout()
        content_row.setSpacing(12)
        layout.addLayout(content_row, 1)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list_widget.currentItemChanged.connect(self._on_card_highlighted)
        content_row.addWidget(self.list_widget, 1)

        self.image_label = QtWidgets.QLabel("Select a card to preview the image.")
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setMinimumSize(260, 200)
        self.image_label.setMaximumWidth(500)
        self.image_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.image_label.setWordWrap(True)
        self.image_label.setFrameShape(QtWidgets.QFrame.Box)
        self.image_label.setStyleSheet("background: #f7f7f7;")
        self.image_label.setScaledContents(False)
        content_row.addWidget(self.image_label, 2)

    def _on_scan_clicked(self) -> None:
        selection = choose_image_folder(parent=self)
        if selection is None:
            return
        folder_path, files = selection
        cards = [card.to_dict() for card in images_to_cards(files)]
        save_folder_cards(folder_path, cards)
        self.cards = cards
        self._refresh_list(cards, folder_path)

    def _refresh_list(self, cards: List[Dict[str, object]], folder_path: str) -> None:
        self.list_widget.clear()
        if not cards:
            self.list_widget.addItem(f"No images found in {folder_path}.")
            return

        for card in cards:
            name = str(card.get("name", "Unknown"))
            path = str(card.get("file_path", ""))
            item = QtWidgets.QListWidgetItem(f"{name} - {path}")
            item.setData(QtCore.Qt.UserRole, path)
            self.list_widget.addItem(item)
        if cards:
            self.list_widget.setCurrentRow(0)

    def _load_cached_cards(self) -> None:
        cache = _load_cache()
        folders = cache.get("folders", {}) if isinstance(cache, dict) else {}
        cards: List[Dict[str, object]] = []
        if isinstance(folders, dict):
            for data in folders.values():
                if isinstance(data, dict):
                    stored = data.get("cards", [])
                    if isinstance(stored, list):
                        cards.extend(stored)

        self.cards = cards
        self.list_widget.clear()
        if cards:
            for card in cards:
                name = str(card.get("name", "Unknown"))
                path = str(card.get("file_path", ""))
                item = QtWidgets.QListWidgetItem(f"{name} - {path}")
                item.setData(QtCore.Qt.UserRole, path)
                self.list_widget.addItem(item)
            self.list_widget.setCurrentRow(0)
        else:
            self.list_widget.addItem("No cached data. Scan a folder to begin.")

    def _on_clear_clicked(self) -> None:
        clear_cache()
        self.cards = []
        self.list_widget.clear()
        self.list_widget.addItem("Cache cleared. Scan a folder to begin.")
        self.image_label.setText("Select a card to preview the image.")
        self.image_label.setPixmap(QtGui.QPixmap())

    def _on_card_highlighted(
        self,
        current: QtWidgets.QListWidgetItem,
        previous: QtWidgets.QListWidgetItem = None,
    ) -> None:
        path = current.data(QtCore.Qt.UserRole) if current else None
        if not path:
            return
        pixmap = QtGui.QPixmap(str(path))
        if pixmap.isNull():
            self.image_label.setText("Unable to load image preview.")
            self.image_label.setPixmap(QtGui.QPixmap())
            return
        target_size = self.image_label.size()
        scaled = pixmap.scaled(
            target_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        self.image_label.setText("")


def _data_file_path() -> Path:
    base = Path(appdirs.user_data_dir("image-search-app", None))
    base.mkdir(parents=True, exist_ok=True)
    return base / "appData.json"


def _load_cache() -> Dict[str, object]:
    path = _data_file_path()
    if not path.exists():
        return {"folders": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"folders": {}}


def _save_cache(data: Dict[str, object]) -> None:
    path = _data_file_path()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_cache() -> None:
    path = _data_file_path()
    if path.exists():
        try:
            path.unlink()
        except Exception:
            # If deletion fails, overwrite with empty cache.
            path.write_text(json.dumps({"folders": {}}), encoding="utf-8")


def save_folder_cards(folder_path: str, cards: List[Dict[str, object]]) -> None:
    """Persist card data for a folder, replacing any previous scan."""
    cache = _load_cache()
    folders: Dict[str, object] = cache.setdefault("folders", {})  # type: ignore[assignment]
    folders[folder_path] = {
        "folder_path": folder_path,
        "last_scanned": datetime.now(timezone.utc).isoformat(),
        "card_count": len(cards),
        "cards": cards,
    }
    _save_cache(cache)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = SearchWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
