from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LoopMode(str, Enum):
    OFF = "off"
    TRACK = "track"
    QUEUE = "queue"


@dataclass(frozen=True, slots=True)
class Track:
    title: str
    stream_url: str
    requested_by: int
    original_query: str
    webpage_url: str | None = None
    duration_seconds: int | None = None

    @property
    def safe_title(self) -> str:
        normalized = " ".join(self.title.split())
        return normalized[:200] or "Unknown title"
