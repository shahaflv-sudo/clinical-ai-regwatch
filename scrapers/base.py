from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ScrapedDoc:
    source: str
    source_id: str
    url: str
    title: str
    raw_text: str
    region: str
    published_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseScraper(ABC):
    source: str = ""
    region: str = ""

    @abstractmethod
    def fetch(self) -> list[ScrapedDoc]:
        """Return all currently-listed documents from this source."""
