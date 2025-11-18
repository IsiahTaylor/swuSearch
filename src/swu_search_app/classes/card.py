"""Card domain model."""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class Card:
    """Minimal representation of a card derived from an pdf file."""

    name: str
    file_path: str
    size_bytes: int
    modified_ts: float
    text: str = ""

    @classmethod
    def from_path(
        cls, path: Path, *, card_type: Optional[str] = None, text: str = ""
    ) -> "Card":
        """Create a Card using the filename for the name, stats for metadata, and optional text."""
        card_type = card_type or cls.__name__
        stat = path.stat()
        return cls(
            name=path.stem,
            file_path=str(path),
            size_bytes=stat.st_size,
            modified_ts=stat.st_mtime,
            text=text,
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "file_path": self.file_path,
            "size_bytes": self.size_bytes,
            "modified_ts": self.modified_ts,
            "text": self.text,
        }
