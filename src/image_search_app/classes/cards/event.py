from dataclasses import dataclass

from image_search_app.classes.card import Card


@dataclass
class Event(Card):
    """Event card."""

    # Type is inferred by Card.from_path when instantiated via this subclass.
    pass
