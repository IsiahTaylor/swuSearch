"""Simple PyQt5 window with an image folder picker, card list, and preview."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import appdirs
from PyQt5 import QtCore, QtGui, QtWidgets

from image_search_app.scripts.search_for_img_file import choose_image_folder
from image_search_app.scripts.scan_worker import ScanWorker


class SearchWindow(QtWidgets.QWidget):
    """Window that lets users pick a folder and view discovered images."""

    ALLOWED_FIELDS = {"file_path", "size_bytes", "modified_ts", "scanned_text"}

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image Search")
        self.resize(900, 675)
        self.cards: List[Dict[str, object]] = []
        self._scan_thread: Optional[QtCore.QThread] = None
        self._scan_worker: Optional[ScanWorker] = None
        self._apply_dark_theme()
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

        self.search_button = QtWidgets.QPushButton("Scan PDF Folder")
        self.search_button.clicked.connect(self._on_scan_clicked)
        controls.addWidget(self.search_button)

        self.cancel_button = QtWidgets.QPushButton("Cancel Scan")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel_scan)
        controls.addWidget(self.cancel_button)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Horizontal splitter for list and preview.
        split_horizontal = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        split_horizontal.setHandleWidth(6)
        layout.addWidget(split_horizontal, 1)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list_widget.currentItemChanged.connect(self._on_card_highlighted)
        split_horizontal.addWidget(self.list_widget)

        self.image_label = QtWidgets.QLabel("Select a card to preview the image.")
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setMinimumSize(260, 200)
        self.image_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.image_label.setWordWrap(True)
        self.image_label.setFrameShape(QtWidgets.QFrame.Box)
        self.image_label.setStyleSheet("background: #1c1c1c; border: 1px solid #333;")
        self.image_label.setScaledContents(False)
        split_horizontal.addWidget(self.image_label)
        split_horizontal.setStretchFactor(0, 1)
        split_horizontal.setStretchFactor(1, 2)

        # Vertical splitter to make JSON area resizable.
        split_vertical = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        split_vertical.setHandleWidth(6)
        split_vertical.addWidget(split_horizontal)

        self.json_view = QtWidgets.QTextEdit()
        self.json_view.setReadOnly(True)
        self.json_view.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.json_view.setMinimumHeight(90)
        self.json_view.setPlaceholderText("Card data will appear here as JSON.")
        font = self.json_view.font()
        font.setFamily("Consolas")
        self.json_view.setFont(font)
        split_vertical.addWidget(self.json_view)
        split_vertical.setStretchFactor(0, 4)
        split_vertical.setStretchFactor(1, 1)

        layout.addWidget(split_vertical, 1)

    def _apply_dark_theme(self) -> None:
        """Apply a simple dark theme to the window and its children."""
        self.setObjectName("searchWindow")
        self.setStyleSheet(
            """
            #searchWindow { background-color: #0f0f0f; color: #f5f5f5; }
            QLabel { color: #f5f5f5; }
            QPushButton {
                background-color: #1f1f1f;
                color: #f5f5f5;
                border: 1px solid #333;
                padding: 6px 10px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #262626; }
            QPushButton:pressed { background-color: #2d2d2d; }
            QPushButton:disabled { color: #777; }
            QListWidget, QTextEdit {
                background-color: #141414;
                color: #e8e8e8;
                border: 1px solid #333;
            }
            QListWidget::item { background: #141414; color: #e8e8e8; }
            QListWidget::item:alternate { background: #1a1a1a; }
            QListWidget::item:selected { background: #2a2a2a; color: #ffffff; }
            QProgressBar {
                background-color: #141414;
                color: #f5f5f5;
                border: 1px solid #333;
                text-align: center;
            }
            QProgressBar::chunk { background-color: #2e7d32; }
            QScrollBar:vertical {
                background: #0f0f0f;
                width: 12px;
                margin: 0px;
            }
            QScrollBar:horizontal {
                background: #0f0f0f;
                height: 12px;
                margin: 0px;
            }
            QScrollBar::handle {
                background: #333;
                border-radius: 4px;
                min-height: 20px;
                min-width: 20px;
            }
            QScrollBar::handle:hover { background: #4a4a4a; }
            QScrollBar::add-line, QScrollBar::sub-line { background: none; height: 0; width: 0; }
            QScrollBar::add-page, QScrollBar::sub-page { background: none; }
            """
        )

    def _on_scan_clicked(self) -> None:
        selection = choose_image_folder(parent=self)
        if selection is None:
            return
        folder_path, files = selection
        if not files:
            self._refresh_list([], folder_path)
            return
        self._start_scan(folder_path, files)

    def _start_scan(self, folder_path: str, files: List[str]) -> None:
        # Clean up any prior worker/thread.
        if self._scan_thread:
            self._scan_thread.quit()
            self._scan_thread.wait()
            self._scan_thread = None
            self._scan_worker = None

        self.search_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(files))
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"Scanning 0/{len(files)}")

        thread = QtCore.QThread()
        worker = ScanWorker(files)
        worker.moveToThread(thread)
        worker.progress.connect(self._on_scan_progress)
        worker.finished.connect(lambda cards: self._on_scan_finished(folder_path, cards))
        worker.cancelled.connect(self._on_scan_cancelled)
        worker.error.connect(self._on_scan_error)
        worker.finished.connect(self._cleanup_scan)
        worker.cancelled.connect(self._cleanup_scan)
        thread.started.connect(worker.run)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    def _cleanup_scan(self) -> None:
        self.search_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        if self._scan_thread:
            self._scan_thread.quit()
            self._scan_thread.wait()
            self._scan_thread = None
            self._scan_worker = None

    def _on_scan_progress(self, processed: int, total: int) -> None:
        self.progress_bar.setMaximum(max(1, total))
        self.progress_bar.setValue(processed)
        self.progress_bar.setFormat(f"Scanning {processed}/{total}")

    def _on_cancel_scan(self) -> None:
        if self._scan_worker:
            self._scan_worker.request_cancel()

    def _on_scan_finished(self, folder_path: str, cards: List[object]) -> None:
        # Persist raw scan output (file metadata + scanned text only).
        normalized = [_normalize_card(card, self.ALLOWED_FIELDS) for card in cards]
        save_folder_cards(folder_path, normalized)
        cache = _load_cache()
        merged_cards = _collect_cards(cache, preferred_path=folder_path, allowed=self.ALLOWED_FIELDS)
        self.cards = merged_cards
        self._refresh_list(merged_cards, "cached folders")
        self._update_json_display(merged_cards[0] if merged_cards else None)

    def _on_scan_cancelled(self, cards: List[object]) -> None:
        self._refresh_list([], "scan cancelled")
        self._update_json_display(None)

    def _on_scan_error(self, message: str) -> None:
        QtWidgets.QMessageBox.warning(self, "Scan Warning", message)

    def _refresh_list(self, cards: List[Dict[str, object]], folder_path: str) -> None:
        self.list_widget.clear()
        if not cards:
            self.list_widget.addItem(f"No PDFs found in {folder_path}.")
            self._update_json_display(None)
            return

        normalized_cards = [_normalize_card(card, self.ALLOWED_FIELDS) for card in cards]
        for card in normalized_cards:
            data = self._extract_card_data(card)
            path = str(self._extract_file_path(data))
            name = Path(path).name if path else "Unknown"
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.UserRole, path)
            self.list_widget.addItem(item)
        self.cards = normalized_cards
        if normalized_cards:
            self.list_widget.setCurrentRow(0)
            self._update_json_display(normalized_cards[0])
        else:
            self._update_json_display(None)

    def _load_cached_cards(self) -> None:
        cache = _load_cache()
        # Migrate any legacy entries to the slim schema and persist.
        folders = cache.get("folders", {}) if isinstance(cache, dict) else {}
        if isinstance(folders, dict):
            changed = False
            for folder_path, folder_data in list(folders.items()):
                if not isinstance(folder_data, dict):
                    continue
                raw_cards = folder_data.get("cards", [])
                normalized_cards = [_normalize_card(c, self.ALLOWED_FIELDS) for c in raw_cards]
                if raw_cards != normalized_cards:
                    folder_data["cards"] = normalized_cards
                    changed = True
            if changed:
                _save_cache(cache)

        cards = _collect_cards(cache, allowed=self.ALLOWED_FIELDS)

        self.cards = cards
        self.list_widget.clear()
        if cards:
            for card in cards:
                data = self._extract_card_data(card)
                name = Path(str(self._extract_file_path(card))).name
                path = str(self._extract_file_path(card))
                item = QtWidgets.QListWidgetItem(name)
                item.setData(QtCore.Qt.UserRole, path)
                self.list_widget.addItem(item)
            self.list_widget.setCurrentRow(0)
            self._update_json_display(cards[0])
        else:
            self.list_widget.addItem("No cached data. Scan a folder to begin.")
            self._update_json_display(None)

    def _on_clear_clicked(self) -> None:
        clear_cache()
        self.cards = []
        self.list_widget.clear()
        self.list_widget.addItem("Cache cleared. Scan a folder to begin.")
        self.image_label.setText("Select a card to preview the image.")
        self.image_label.setPixmap(QtGui.QPixmap())
        self._update_json_display(None)

    def _on_card_highlighted(
        self,
        current: QtWidgets.QListWidgetItem,
        previous: QtWidgets.QListWidgetItem = None,
    ) -> None:
        path = current.data(QtCore.Qt.UserRole) if current else None
        if not path:
            self._update_json_display(None)
            return
        pixmap = QtGui.QPixmap(str(path))
        if pixmap.isNull():
            self.image_label.setText("Unable to load image preview.")
            self.image_label.setPixmap(QtGui.QPixmap())
            self._update_json_display(None)
            return
        target_size = self.image_label.size()
        scaled = pixmap.scaled(
            target_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        self.image_label.setText("")
        self._update_json_display(self._find_card_by_path(str(path)))

    def _find_card_by_path(self, path: str) -> Optional[Dict[str, object]]:
        for card in self.cards:
            normalized = _normalize_card(card, self.ALLOWED_FIELDS)
            if self._extract_file_path(normalized) == path:
                return normalized
        return None

    def _extract_file_path(self, card: Dict[str, object]) -> str:
        if isinstance(card, dict):
            if "file_path" in card:
                return str(card.get("file_path", ""))
            if len(card) == 1:
                inner = next(iter(card.values()))
                if isinstance(inner, dict):
                    return str(inner.get("file_path", ""))
        return ""

    def _extract_card_data(self, card: Dict[str, object]) -> Dict[str, object]:
        if isinstance(card, dict):
            normalized = _normalize_card(card, self.ALLOWED_FIELDS)
            if normalized:
                return normalized
        return {}

    def _update_json_display(self, card: Optional[Dict[str, object]]) -> None:
        payload: Dict[str, object] = card or {"card": None}
        try:
            text = json.dumps(payload, indent=2, ensure_ascii=False)
        except Exception:
            text = "Unable to render card data."
        self.json_view.setPlainText(text)


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


def _collect_cards(
    cache: Dict[str, object], preferred_path: Optional[str] = None, *, allowed: Optional[set] = None
) -> List[Dict[str, object]]:
    folders = cache.get("folders", {}) if isinstance(cache, dict) else {}
    if not isinstance(folders, dict):
        return []

    items = list(folders.items())
    if preferred_path and preferred_path in folders:
        preferred = folders[preferred_path]
        items = [(k, v) for k, v in items if k != preferred_path]
        items.append((preferred_path, preferred))

    by_file: Dict[str, Dict[str, object]] = {}
    for _, data in items:
        if not isinstance(data, dict):
            continue
        stored = data.get("cards", [])
        if not isinstance(stored, list):
            continue
        for card in stored:
            if not isinstance(card, dict):
                continue
            file_path = str(card.get("file_path", ""))
            if not file_path:
                continue
            normalized = _normalize_card(card, allowed) if allowed else card
            by_file[file_path] = normalized

    return list(by_file.values())


def _normalize_card(card: Dict[str, object], allowed: set) -> Dict[str, object]:
    """Return a dict containing only the allowed keys if present."""
    if not isinstance(card, dict):
        return {}
    # If wrapped (legacy), unwrap the inner dict.
    if len(card) == 1 and not any(k in allowed for k in card):
        inner = next(iter(card.values()))
        if isinstance(inner, dict):
            card = inner
    return {k: card[k] for k in allowed if k in card}


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
