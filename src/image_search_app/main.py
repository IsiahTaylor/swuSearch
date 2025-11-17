"""Simple PyQt5 window with an image folder picker and card list."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import appdirs
from PyQt5 import QtWidgets

from image_search_app.scripts.batch_img_to_card import images_to_cards
from image_search_app.scripts.search_for_img_file import choose_image_folder


class SearchWindow(QtWidgets.QWidget):
    """Window that lets users pick a folder and view discovered images."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image Search")
        self.resize(500, 400)
        self.cards: List[Dict[str, object]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.search_button = QtWidgets.QPushButton("Scan Image Folder")
        self.search_button.clicked.connect(self._on_scan_clicked)
        layout.addWidget(self.search_button)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        layout.addWidget(self.list_widget, 1)

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
            item = QtWidgets.QListWidgetItem(f"{name} — {path}")
            self.list_widget.addItem(item)


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
