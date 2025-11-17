"""Convert batches of image files into Card objects."""
from typing import Iterable, List

from image_search_app.classes.card import Card
from image_search_app.scripts.img_to_card import image_to_card


def images_to_cards(image_paths: Iterable[str]) -> List[Card]:
    """Create Card (or subclass) objects for each image path."""
    cards: List[Card] = []
    for path_str in image_paths:
        card = image_to_card(path_str)
        if card is not None:
            cards.append(card)
        else:
            # Ensure we always return a list aligned to the provided paths,
            # even if OCR is unavailable for a given file.
            continue
    return cards
