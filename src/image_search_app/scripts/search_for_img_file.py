"""Helper to let the user choose a folder of PDFs to scan."""
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt5 import QtWidgets


def choose_image_folder(parent: QtWidgets.QWidget | None = None) -> Optional[Tuple[str, List[str]]]:
    """
    Show a file picker for PDFs and return the selected files plus their folder.

    Returns:
        (folder_path, pdf_paths) if files are selected, otherwise None.
    """
    dialog = QtWidgets.QFileDialog(parent, "Select PDF files")
    dialog.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
    dialog.setNameFilters(["PDF Files (*.pdf)", "All Files (*)"])
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        return None

    selected = dialog.selectedFiles()
    pdfs = [str(Path(path)) for path in selected if path.lower().endswith(".pdf")]
    if not pdfs:
        return None

    folder_path = str(Path(pdfs[0]).parent)
    return folder_path, sorted(pdfs)
