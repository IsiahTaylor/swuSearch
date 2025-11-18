"""Convert PDF pages into simple dict records using text extraction (no OCR)."""
from pathlib import Path
from typing import Dict, Optional
import tempfile

import fitz  # PyMuPDF

PREVIEW_DPI = 300
EXPORT_TARGET_WIDTH = 745
EXPORT_TARGET_HEIGHT = 1040
EXPORT_DPI = 300


def get_pdf_page_count(pdf_path: str) -> int:
    with fitz.open(pdf_path) as doc:
        return doc.page_count


def pdf_page_to_card(pdf_path: str, page_index: int) -> Optional[Dict[str, object]]:
    """Convert a single PDF page to a simple card dict."""
    path = Path(pdf_path)
    if not path.is_file():
        return None
    stat = path.stat()

    with fitz.open(pdf_path) as doc:
        if page_index < 0 or page_index >= doc.page_count:
            return None
        page = doc.load_page(page_index)
        text = page.get_text("text") or ""
        # Flatten newlines so downstream searches can match across line breaks.
        text = text.replace("\n", " ")

        # Save a page preview image for the UI.
        pix = page.get_pixmap(dpi=PREVIEW_DPI)
        preview_path = Path(tempfile.gettempdir()) / f"{path.stem}_p{page_index + 1}.png"
        pix.save(preview_path)

    full_text = text

    file_ref = str(preview_path)

    return {
        "file_path": file_ref,  # preview image path
        "pdf_path": str(path),
        "page_index": page_index,
        "size_bytes": stat.st_size,
        "modified_ts": stat.st_mtime,
        "scanned_text": full_text,
    }
