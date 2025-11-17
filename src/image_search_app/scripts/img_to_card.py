"""Convert a single image into a typed Card model using OCR."""
from pathlib import Path
from typing import Optional
import os

import cv2
import pytesseract

from image_search_app.classes.card import Card
from image_search_app.classes.cards.event import Event
from image_search_app.classes.cards.leader import Leader
from image_search_app.classes.cards.unit import Unit
from image_search_app.classes.cards.upgrade import Upgrade


def _prepare_header(image):
    """
    Boost small header text: convert to grayscale, upscale, and binarize.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    scaled = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    filtered = cv2.bilateralFilter(scaled, d=5, sigmaColor=75, sigmaSpace=75)
    _, bw = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return bw


def _ensure_pytesseract_ready() -> None:
    """
    Verify the Tesseract binary is available. pytesseract raises if not found.
    """
    try:
        pytesseract.get_tesseract_version()
    except Exception as exc:
        raise RuntimeError(f"Tesseract is not available: {exc}") from exc


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


def _ocr_text(image, psm: int = 3, oem: int = 3) -> str:
    """
    Run OCR on an OpenCV image. Handles BGR or grayscale input.
    """
    if len(image.shape) == 2:
        rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    else:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    config = f"--oem {oem} --psm {psm}"
    text = pytesseract.image_to_string(rgb, lang="eng", config=config)
    return " ".join(text.split())


def image_to_card(path_str: str) -> Optional[Card]:
    """Convert a single image path to a Card (or subclass) with OCR text."""
    path = Path(path_str)
    if not path.is_file():
        return None

    image = cv2.imread(str(path))
    if image is None:
        return Card.from_path(path, text="")

    # Allow overriding tesseract binary via env var if PATH is not picked up.
    custom_tess = os.environ.get("TESSERACT_CMD")
    if custom_tess:
        pytesseract.pytesseract.tesseract_cmd = custom_tess

    try:
        _ensure_pytesseract_ready()
    except Exception as exc:
        # Surface as a simple failure without crashing the app.
        print(f"[WARN] OCR unavailable: {exc}")
        return Card.from_path(path, text="")

    # Read top 6% of the image to detect type.
    height = image.shape[0]
    header_height = max(1, int(height * 0.06))
    header = image[:header_height, :, :]
    prepped_header = _prepare_header(header)
    top_text = _ocr_text(prepped_header, psm=7)
    card_type = _detect_type(top_text) if top_text else "Card"

    # Full text for the card.
    full_text = _ocr_text(image, psm=3)

    cls_map = {
        "Event": Event,
        "Unit": Unit,
        "Upgrade": Upgrade,
        "Leader": Leader,
    }
    cls = cls_map.get(card_type, Card)
    return cls.from_path(path, card_type=card_type, text=full_text)
