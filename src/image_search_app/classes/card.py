"""Card domain model."""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass
class Card:
    """Minimal representation of a card derived from an image file."""

    name: str
    file_path: str
    size_bytes: int
    modified_ts: float

    @classmethod
    def from_path(cls, path: Path) -> "Card":
        """Create a Card using the filename for the name and file stats for metadata."""
        stat = path.stat()
        return cls(
            name=path.stem,
            file_path=str(path),
            size_bytes=stat.st_size,
            modified_ts=stat.st_mtime,
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "file_path": self.file_path,
            "size_bytes": self.size_bytes,
            "modified_ts": self.modified_ts,
        }
