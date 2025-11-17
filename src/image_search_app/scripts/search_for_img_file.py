"""Utilities for selecting a folder and collecting PDF file paths."""
from pathlib import Path
from typing import List, Optional

try:
    # Imported lazily so this module stays usable from both GUI and CLI contexts.
    from PyQt5 import QtWidgets
except ImportError:
    QtWidgets = None  # type: ignore


PDF_EXTENSIONS = {".pdf"}


def choose_image_folder(parent: Optional[object] = None) -> Optional[tuple[str, List[str]]]:
    """Open a folder picker and return (folder_path, pdf_file_paths)."""
    if QtWidgets is None:
        raise RuntimeError("PyQt5 is required for choose_image_files")

    folder = QtWidgets.QFileDialog.getExistingDirectory(
        parent,
        "Select Folder Containing PDFs",
        "",
        QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks,
    )
    if not folder:
        return None

    base = Path(folder)
    files = [
        str(path)
        for path in sorted(base.rglob("*"))
        if path.is_file() and path.suffix.lower() in PDF_EXTENSIONS
    ]
    return folder, files
