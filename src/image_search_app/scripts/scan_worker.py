"""Background worker for scanning images into Card objects."""
import concurrent.futures
import threading
from typing import List

from PyQt5 import QtCore

from image_search_app.scripts.img_to_card import image_to_card


class ScanWorker(QtCore.QObject):
    """Worker object to scan images on a background thread with progress signals."""

    progress = QtCore.pyqtSignal(int, int)  # processed, total
    finished = QtCore.pyqtSignal(list)
    cancelled = QtCore.pyqtSignal(list)
    error = QtCore.pyqtSignal(str)

    def __init__(self, paths: List[str]) -> None:
        super().__init__()
        self._paths = paths
        self._stop_event = threading.Event()

    def request_cancel(self) -> None:
        self._stop_event.set()

    @QtCore.pyqtSlot()
    def run(self) -> None:
        total = len(self._paths)
        processed = 0
        cards: List[object] = []
        self.progress.emit(processed, total)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(image_to_card, path): path for path in self._paths}
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
