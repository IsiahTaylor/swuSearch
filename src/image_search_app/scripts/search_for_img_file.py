"""Utilities for selecting PDFs (via file picker) and collecting file paths."""
from pathlib import Path
from typing import List, Optional

try:
    # Imported lazily so this module stays usable from both GUI and CLI contexts.
    from PyQt5 import QtWidgets
except ImportError:
    QtWidgets = None  # type: ignore


PDF_EXTENSIONS = {".pdf"}


def choose_image_folder(parent: Optional[object] = None) -> Optional[tuple[str, List[str]]]:
    """Open a file picker and return (folder_path, pdf_file_paths)."""
    if QtWidgets is None:
        raise RuntimeError("PyQt5 is required for choose_image_files")

    dialog = QtWidgets.QFileDialog(parent, "Select PDFs")
    dialog.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
    dialog.setNameFilter("PDF Files (*.pdf)")
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        return None

    files = dialog.selectedFiles()
    if not files:
        return None
    base_folder = str(Path(files[0]).parent)
    return base_folder, files
