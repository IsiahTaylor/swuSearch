"""Basic PyQt5 application for searching text within a PDF file.

Install dependencies:
    pip install PyQt5 PyPDF2
"""
import sys
from pathlib import Path
from typing import List, Optional

from PyQt5 import QtWidgets


try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None


class PdfSearchWindow(QtWidgets.QMainWindow):
    """Small helper window that loads a PDF and searches for text."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF Search")
        self.resize(800, 600)

        self._current_file: Optional[Path] = None
        self._pdf_pages: List[str] = []

        self._build_ui()

    def _build_ui(self) -> None:
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        file_row = QtWidgets.QHBoxLayout()
        self.file_label = QtWidgets.QLabel("No PDF loaded")
        file_row.addWidget(self.file_label, 1)

        open_button = QtWidgets.QPushButton("Open PDF...")
        open_button.clicked.connect(self.open_pdf)
        file_row.addWidget(open_button)

        layout.addLayout(file_row)

        search_row = QtWidgets.QHBoxLayout()
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Enter the text you want to find")
        self.search_input.returnPressed.connect(self.perform_search)
        search_row.addWidget(self.search_input, 1)

        search_button = QtWidgets.QPushButton("Search")
        search_button.clicked.connect(self.perform_search)
        search_row.addWidget(search_button)

        layout.addLayout(search_row)

        self.result_box = QtWidgets.QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setPlaceholderText("Search results will appear here.")
        layout.addWidget(self.result_box, 1)

        self.feedback_label = QtWidgets.QLabel("Select a PDF to begin.")
        layout.addWidget(self.feedback_label)

    def open_pdf(self) -> None:
        if PdfReader is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing dependency",
                "PyPDF2 is required to open PDF files.\nRun: pip install PyPDF2",
            )
            return

        start_dir = (
            str(self._current_file.parent)
            if self._current_file and self._current_file.exists()
            else str(Path.home())
        )

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select PDF file",
            start_dir,
            "PDF Files (*.pdf)",
        )
        if not file_path:
            return

        try:
            reader = PdfReader(file_path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Unable to open PDF", str(exc))
            return

        pages: List[str] = []
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            pages.append(text)

        if not pages:
            QtWidgets.QMessageBox.information(
                self,
                "Empty document",
                "No pages were detected in the selected PDF.",
            )

        self._pdf_pages = pages
        self._current_file = Path(file_path)
        self.file_label.setText(self._current_file.name)
        self.result_box.clear()

        if any(text.strip() for text in pages):
            self.feedback_label.setText(
                f"Loaded {len(self._pdf_pages)} page(s). Ready to search."
            )
        else:
            self.feedback_label.setText(
                "PDF loaded, but no extractable text was found."
            )

    def perform_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            self.feedback_label.setText("Enter a search term first.")
            return

        if not self._pdf_pages:
            self.feedback_label.setText("Open a PDF before searching.")
            return

        lowered = query.lower()
        matches = []
        for index, text in enumerate(self._pdf_pages, start=1):
            if lowered in text.lower():
                snippet = self._build_snippet(text, lowered, len(query))
                matches.append(f"Page {index}: {snippet}")

        if matches:
            self.result_box.setPlainText("\n\n".join(matches))
            self.feedback_label.setText(
                f"Found matches on {len(matches)} page(s)."
            )
        else:
            self.result_box.setPlainText("No matches found.")
            self.feedback_label.setText("No matches found.")

    @staticmethod
    def _build_snippet(text: str, lowered: str, query_len: int) -> str:
        lowered_text = text.lower()
        idx = lowered_text.find(lowered)
        if idx == -1:
            return "Match located on this page."
        start = max(0, idx - 80)
        end = min(len(text), idx + query_len + 80)
        snippet = " ".join(text[start:end].split())
        return f"...{snippet}..."


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = PdfSearchWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
