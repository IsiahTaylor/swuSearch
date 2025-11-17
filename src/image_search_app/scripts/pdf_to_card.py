"""Convert PDF pages into Card objects using text extraction (no OCR)."""
from pathlib import Path
from typing import Optional
import tempfile

import fitz  # PyMuPDF

from image_search_app.classes.card import Card
from image_search_app.classes.cards.event import Event
from image_search_app.classes.cards.leader import Leader
from image_search_app.classes.cards.unit import Unit
from image_search_app.classes.cards.upgrade import Upgrade
from image_search_app.scripts.card_classifier import classify_card


def _detect_type(top_text: str) -> str:
    lowered = top_text.lower()
    if "event" in lowered:
        return "Event"
    if "unit" in lowered:
        return "Unit"
    if "upgrade" in lowered:
        return "Upgrade"
    if "leader" in lowered:
        return "Leader"
    return "Card"


def get_pdf_page_count(pdf_path: str) -> int:
    with fitz.open(pdf_path) as doc:
        return doc.page_count


def pdf_page_to_card(pdf_path: str, page_index: int) -> Optional[Card]:
    """Convert a single PDF page to a Card."""
    path = Path(pdf_path)
    if not path.is_file():
        return None
    stat = path.stat()

    with fitz.open(pdf_path) as doc:
        if page_index < 0 or page_index >= doc.page_count:
            return None
        page = doc.load_page(page_index)
        text = page.get_text("text") or ""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        top_text = lines[0] if lines else ""
        card_type = _detect_type(top_text) if top_text else "Card"

        # Save a page preview image for the UI.
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        preview_path = (
            Path(tempfile.gettempdir()) / f"{path.stem}_p{page_index + 1}.png"
        )
        pix.save(preview_path)

    full_text = text

    name = f"{path.stem}_p{page_index + 1}"
    file_ref = str(preview_path)

    cls_map = {
        "Event": Event,
        "Unit": Unit,
        "Upgrade": Upgrade,
        "Leader": Leader,
    }
    cls = cls_map.get(card_type, Card)
    card = cls(
        name=name,
        file_path=file_ref,
        size_bytes=stat.st_size,
        modified_ts=stat.st_mtime,
        type=card_type,
        text=full_text,
    )
    return classify_card(card)