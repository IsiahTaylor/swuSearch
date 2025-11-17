"""Utilities for selecting a folder and collecting image file paths."""
from pathlib import Path
from typing import List, Optional

try:
    # Imported lazily so this module stays usable from both GUI and CLI contexts.
    from PyQt5 import QtWidgets
except ImportError:
    QtWidgets = None  # type: ignore


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def choose_image_folder(parent: Optional[object] = None) -> Optional[tuple[str, List[str]]]:
    """Open a folder picker and return (folder_path, image_file_paths)."""
    if QtWidgets is None:
        raise RuntimeError("PyQt5 is required for choose_image_files")

    folder = QtWidgets.QFileDialog.getExistingDirectory(
        parent,
        "Select Folder Containing Images",
        "",
        QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks,
    )
    if not folder:
        return None

    base = Path(folder)
    files = [
        str(path)
        for path in sorted(base.rglob("*"))
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return folder, files
