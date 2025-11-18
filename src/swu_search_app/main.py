"""PyQt5 UI for scanning PDFs, browsing page previews, and filtering results."""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import appdirs
from PyQt5 import QtCore, QtGui, QtWidgets

from swu_search_app.scripts.search_for_pdf import choose_pdf_files
from swu_search_app.scripts.scan_worker import ScanWorker
from swu_search_app.scripts.search_filters import filter_cards


class SearchWindow(QtWidgets.QWidget):
    """Window that lets users pick a folder and view discovered images."""

    ALLOWED_FIELDS = {
        "file_path",  # preview image path
        "pdf_path",
        "page_index",
        "size_bytes",
        "modified_ts",
        "scanned_text",
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SWU Search")
        self.resize(900, 675)
        self.cards: List[Dict[str, object]] = []
        self.all_cards: List[Dict[str, object]] = []
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

        # Filter inputs under the control row.
        filter_row = QtWidgets.QHBoxLayout()
        filter_row.setSpacing(8)
        layout.addLayout(filter_row)

        filter_row.addWidget(QtWidgets.QLabel("Include:"))
        self.include_input = QtWidgets.QLineEdit()
        self.include_input.setPlaceholderText(
            'e.g. apple AND orange or "exact phrase"; "*" only works inside quotes'
        )
        self.include_input.returnPressed.connect(self._on_filter_apply)
        filter_row.addWidget(self.include_input, 1)

        filter_row.addWidget(QtWidgets.QLabel("Exclude:"))
        self.exclude_input = QtWidgets.QLineEdit()
        self.exclude_input.setPlaceholderText(
            'e.g. NOT used; OR/AND/() allowed; "*" only works inside quotes'
        )
        self.exclude_input.returnPressed.connect(self._on_filter_apply)
        filter_row.addWidget(self.exclude_input, 1)

        self.apply_filter_button = QtWidgets.QPushButton("Apply Filter")
        self.apply_filter_button.clicked.connect(self._on_filter_apply)
        filter_row.addWidget(self.apply_filter_button)

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

        self.list_widget = QtWidgets.QTreeWidget()
        self.list_widget.setHeaderHidden(True)
        self.list_widget.setIndentation(18)
        self.list_widget.setUniformRowHeights(True)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.currentItemChanged.connect(self._on_card_highlighted)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.itemChanged.connect(self._on_check_changed)
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_widget.installEventFilter(self)
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
        self.json_view.setMinimumHeight(140)
        self.json_view.setPlaceholderText("Card data will appear here as JSON.")
        font = self.json_view.font()
        font.setFamily("Consolas")
        self.json_view.setFont(font)
        split_vertical.addWidget(self.json_view)
        split_vertical.setStretchFactor(0, 3)
        split_vertical.setStretchFactor(1, 2)

        layout.addWidget(split_vertical, 1)

        # Footer row with selection count and export action.
        footer = QtWidgets.QHBoxLayout()
        footer.addStretch()
        self.selected_count_label = QtWidgets.QLabel("Selected: 0")
        footer.addWidget(self.selected_count_label)
        self.export_button = QtWidgets.QPushButton("Export Selected")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_selected_previews)
        footer.addWidget(self.export_button)
        layout.addLayout(footer)

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
            QListWidget, QTreeWidget, QTextEdit, QLineEdit {
                background-color: #141414;
                color: #e8e8e8;
                border: 1px solid #333;
            }
            QListWidget::item, QTreeWidget::item { background: #141414; color: #e8e8e8; }
            QListWidget::item:alternate, QTreeWidget::item:alternate { background: #1a1a1a; }
            QListWidget::item:selected, QTreeWidget::item:selected { background: #2a2a2a; color: #ffffff; }
            QLineEdit {
                background-color: #1f2a36;
                border: 1px solid #2f3b47;
                padding: 4px 6px;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #3f5366;
            }
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
        selection = choose_pdf_files(parent=self)
        if selection is None:
            return
        folder_path, pdf_files = selection
        if not pdf_files:
            self._refresh_list([], folder_path)
            return
        self._start_scan(folder_path, pdf_files)

    def _start_scan(self, folder_path: str, pdf_files: List[str]) -> None:
        # Clean up any prior worker/thread.
        if self._scan_thread:
            self._scan_thread.quit()
            self._scan_thread.wait()
            self._scan_thread = None
            self._scan_worker = None

        self.search_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(pdf_files))
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"Scanning 0/{len(pdf_files)}")

        thread = QtCore.QThread()
        worker = ScanWorker(pdf_files)
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
        self._update_filter_placeholders()

    def _on_scan_cancelled(self, cards: List[object]) -> None:
        self._refresh_list([], "scan cancelled")
        self._update_json_display(None)

    def _on_scan_error(self, message: str) -> None:
        QtWidgets.QMessageBox.warning(self, "Scan Warning", message)

    def _refresh_list(
        self, cards: List[Dict[str, object]], folder_path: str, *, store_all: bool = True
    ) -> None:
        self.list_widget.clear()
        if not cards:
            empty = QtWidgets.QTreeWidgetItem([f"No PDFs found in {folder_path}."])
            self.list_widget.addTopLevelItem(empty)
            self._update_json_display(None)
            return

        normalized_cards = [_normalize_card(card, self.ALLOWED_FIELDS) for card in cards]
        parents: Dict[str, QtWidgets.QTreeWidgetItem] = {}
        for idx, card in enumerate(normalized_cards):
            data = self._extract_card_data(card)
            preview_path = str(self._extract_file_path(data))
            pdf_path = str(data.get("pdf_path") or "")
            pdf_name = Path(pdf_path).name if pdf_path else "Unknown file"
            entry_name = Path(preview_path).name or f"Entry {idx + 1}"

            parent_key = pdf_path or pdf_name
            parent = parents.get(parent_key)
            if parent is None:
                parent = QtWidgets.QTreeWidgetItem([pdf_name])
                parent.setFirstColumnSpanned(False)
                parents[parent_key] = parent
                self.list_widget.addTopLevelItem(parent)
            child = QtWidgets.QTreeWidgetItem([f"    {entry_name}"])
            child.setData(0, QtCore.Qt.UserRole, preview_path)
            child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
            child.setCheckState(0, QtCore.Qt.Unchecked)
            parent.addChild(child)

        self.list_widget.expandAll()
        if store_all:
            self.all_cards = normalized_cards
        self.cards = normalized_cards
        first = self.list_widget.topLevelItem(0)
        if first and first.childCount() > 0:
            self.list_widget.setCurrentItem(first.child(0))
            self._update_json_display(normalized_cards[0])
        else:
            self._update_json_display(None)
        self._update_selection_state()

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

        self.all_cards = cards
        self.cards = cards
        self.list_widget.clear()
        if cards:
            parents: Dict[str, QtWidgets.QTreeWidgetItem] = {}
            for idx, card in enumerate(cards):
                data = self._extract_card_data(card)
                preview_path = str(self._extract_file_path(card))
                pdf_path = str(data.get("pdf_path") or "")
                pdf_name = Path(pdf_path).name if pdf_path else "Unknown file"
                entry_name = Path(preview_path).name or f"Entry {idx + 1}"

                parent_key = pdf_path or pdf_name
                parent = parents.get(parent_key)
                if parent is None:
                    parent = QtWidgets.QTreeWidgetItem([pdf_name])
                    parents[parent_key] = parent
                    self.list_widget.addTopLevelItem(parent)
                child = QtWidgets.QTreeWidgetItem([f"    {entry_name}"])
                child.setData(0, QtCore.Qt.UserRole, preview_path)
                child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                child.setCheckState(0, QtCore.Qt.Unchecked)
                parent.addChild(child)
            self.list_widget.expandAll()
            first = self.list_widget.topLevelItem(0)
            if first and first.childCount() > 0:
                self.list_widget.setCurrentItem(first.child(0))
                self._update_json_display(cards[0])
            else:
                self._update_json_display(None)
        else:
            empty = QtWidgets.QTreeWidgetItem(["No cached data. Scan a folder to begin."])
            self.list_widget.addTopLevelItem(empty)
            self._update_json_display(None)
        self._update_selection_state()
        self._update_filter_placeholders()

    def _on_clear_clicked(self) -> None:
        clear_cache()
        self.cards = []
        self.all_cards = []
        self.list_widget.clear()
        empty = QtWidgets.QTreeWidgetItem(["Cache cleared. Scan a folder to begin."])
        self.list_widget.addTopLevelItem(empty)
        self.image_label.setText("Select a card to preview the image.")
        self.image_label.setPixmap(QtGui.QPixmap())
        self._update_json_display(None)
        self._update_selection_state()

    def _on_card_highlighted(
        self,
        current: QtWidgets.QTreeWidgetItem,
        previous: QtWidgets.QTreeWidgetItem = None,
    ) -> None:
        path = current.data(0, QtCore.Qt.UserRole) if current else None
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
        self._update_selection_state()

    def _on_filter_apply(self) -> None:
        include_expr = self.include_input.text()
        exclude_expr = self.exclude_input.text()
        filtered = filter_cards(self.all_cards, include_expr, exclude_expr)
        self._refresh_list(filtered, "filtered results", store_all=False)

    def _update_filter_placeholders(self) -> None:
        total = len(self.all_cards)
        self.include_input.setPlaceholderText(
            (
                f'Include (AND/OR/"", (), "*" in quotes). Cached items: {total}'
                if total
                else 'Include filter (use "*" only inside quotes)'
            )
        )

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

    def _on_selection_changed(self) -> None:
        self._update_selection_state()

    def _on_check_changed(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:  # noqa: ARG002
        self._update_selection_state()

    def _update_selection_state(self) -> None:
        iterator = QtWidgets.QTreeWidgetItemIterator(self.list_widget)
        checked_paths: List[str] = []
        while iterator.value():
            item = iterator.value()
            if (
                item.data(0, QtCore.Qt.UserRole)
                and item.checkState(0) == QtCore.Qt.Checked
            ):
                checked_paths.append(str(item.data(0, QtCore.Qt.UserRole)))
            iterator += 1
        count = len(checked_paths)
        self.selected_count_label.setText(f"Selected: {count}")
        self.export_button.setEnabled(count > 0)

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:  # type: ignore[override]
        if obj is self.list_widget and event.type() == QtCore.QEvent.KeyPress:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                item = self.list_widget.currentItem()
                if item and item.flags() & QtCore.Qt.ItemIsUserCheckable:
                    new_state = (
                        QtCore.Qt.Unchecked
                        if item.checkState(0) == QtCore.Qt.Checked
                        else QtCore.Qt.Checked
                    )
                    item.setCheckState(0, new_state)
                    return True
        return super().eventFilter(obj, event)

    def _export_selected_previews(self) -> None:
        """Copy checked preview images to a user-selected destination folder."""
        iterator = QtWidgets.QTreeWidgetItemIterator(self.list_widget)
        preview_paths: List[str] = []
        while iterator.value():
            item = iterator.value()
            if (
                item.data(0, QtCore.Qt.UserRole)
                and item.checkState(0) == QtCore.Qt.Checked
            ):
                preview_paths.append(str(item.data(0, QtCore.Qt.UserRole)))
            iterator += 1
        if not preview_paths:
            return

        dest_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Select export folder")
        if not dest_dir:
            return

        dest = Path(dest_dir)
        errors: List[str] = []
        for path in preview_paths:
            src = Path(path)
            if not src.exists():
                errors.append(f"Missing: {src}")
                continue
            target = dest / src.name
            try:
                shutil.copy2(src, target)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{src.name}: {exc}")

        if errors:
            QtWidgets.QMessageBox.warning(
                self,
                "Export completed with issues",
                "Some files could not be exported:\n" + "\n".join(errors),
            )
        else:
            QtWidgets.QMessageBox.information(
                self, "Success", f"Exported {len(preview_paths)} file(s) successfully."
            )

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
    base = Path(appdirs.user_data_dir("swu_search_app", None))
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
    """Flatten cached folder entries into a list of cards, preferring the newest folder when provided."""
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
