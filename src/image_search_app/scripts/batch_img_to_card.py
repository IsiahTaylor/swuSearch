"""Convert batches of image files into Card objects."""
from pathlib import Path
from typing import Iterable, List

from image_search_app.classes.card import Card


def images_to_cards(image_paths: Iterable[str]) -> List[Card]:
    """Create Card objects for each image path."""
    cards: List[Card] = []
    for path_str in image_paths:
        path = Path(path_str)
        if not path.is_file():
            continue
        cards.append(Card.from_path(path))
    return cards
