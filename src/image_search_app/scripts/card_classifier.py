"""Heuristics for classifying cards from extracted text."""
from __future__ import annotations

import re

from image_search_app.classes.card import Card

# Simple keyword mapping for now; can be expanded later.
_TYPE_KEYWORDS = [
    ("leader", "Leader"),
    ("unit", "Unit"),
    ("upgrade", "Upgrade"),
    ("event", "Event"),
]


def classify_text(text: str) -> str:
    """Classify a card type based on its text content."""
    lowered = text.lower()
    for needle, label in _TYPE_KEYWORDS:
        if needle in lowered:
            return label
    return "Card"


def classify_card(card: Card) -> Card:
    """
    Update and return the card with a best-guess type based on its text.

    Extend this to add more heuristics (e.g., name patterns, icons, etc.).
    """
    card.type = classify_text(card.text or "")
    return card

