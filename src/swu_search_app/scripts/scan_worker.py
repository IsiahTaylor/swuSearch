"""Background worker for scanning PDFs into simple card dicts."""
import concurrent.futures
import threading
from typing import List, Tuple

from PyQt5 import QtCore

from swu_search_app.scripts.pdf_to_card import pdf_page_to_card, get_pdf_page_count


class ScanWorker(QtCore.QObject):
    """Worker object to scan PDFs on a background thread with progress signals."""

    progress = QtCore.pyqtSignal(int, int)  # processed, total
    finished = QtCore.pyqtSignal(list)
    cancelled = QtCore.pyqtSignal(list)
    error = QtCore.pyqtSignal(str)

    def __init__(self, pdf_paths: List[str]) -> None:
        super().__init__()
        self._pdf_paths = pdf_paths
        self._stop_event = threading.Event()

    def request_cancel(self) -> None:
        self._stop_event.set()

    @QtCore.pyqtSlot()
    def run(self) -> None:
        tasks: List[Tuple[str, int]] = []
        for pdf_path in self._pdf_paths:
            try:
                page_count = get_pdf_page_count(pdf_path)
            except Exception as exc:
                self.error.emit(f"Failed to read PDF {pdf_path}: {exc}")
                continue
            for idx in range(page_count):
                tasks.append((pdf_path, idx))

        total = len(tasks)
        processed = 0
        cards: List[object] = []
        self.progress.emit(processed, total)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(pdf_page_to_card, pdf_path, page_index): (pdf_path, page_index)
                for pdf_path, page_index in tasks
            }
            for future in concurrent.futures.as_completed(futures):
                if self._stop_event.is_set():
                    for fut in futures:
                        fut.cancel()
                    self.cancelled.emit(cards)
                    return
                try:
                    card = future.result()
                    if card is not None:
                        cards.append(card)
                except Exception as exc:
                    # Surface error but continue with remaining files.
                    self.error.emit(str(exc))
                processed += 1
                self.progress.emit(processed, total)

        if self._stop_event.is_set():
            self.cancelled.emit(cards)
        else:
            self.finished.emit(cards)
