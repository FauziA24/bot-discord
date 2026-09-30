from __future__ import annotations

import random
from collections import deque
from collections.abc import Iterable

from .entities import Track


class QueueFullError(RuntimeError):
    """Raised when a guild queue reaches its configured capacity."""


class QueuePositionError(ValueError):
    """Raised when a requested queue position does not exist."""


class GuildQueue:
    """Pure domain queue with no Discord or network dependencies."""

    def __init__(self, max_size: int) -> None:
        if max_size < 1:
            raise ValueError("max_size must be positive")
        self._max_size = max_size
        self._tracks: deque[Track] = deque()

    def __len__(self) -> int:
        return len(self._tracks)

    @property
    def is_full(self) -> bool:
        return len(self._tracks) >= self._max_size

    def enqueue(self, track: Track) -> None:
        if self.is_full:
            raise QueueFullError(f"Queue limit of {self._max_size} tracks reached")
        self._tracks.append(track)

    def dequeue(self) -> Track | None:
        return self._tracks.popleft() if self._tracks else None

    def remove(self, index: int) -> Track:
        self._validate_index(index)
        tracks = list(self._tracks)
        removed = tracks.pop(index)
        self._tracks = deque(tracks)
        return removed

    def move(self, source_index: int, destination_index: int) -> Track:
        self._validate_index(source_index)
        self._validate_index(destination_index)
        tracks = list(self._tracks)
        moved = tracks.pop(source_index)
        tracks.insert(destination_index, moved)
        self._tracks = deque(tracks)
        return moved

    def shuffle(self, rng: random.Random | None = None) -> int:
        tracks = list(self._tracks)
        (rng.shuffle if rng else random.shuffle)(tracks)
        self._tracks = deque(tracks)
        return len(tracks)

    def clear(self) -> int:
        removed_count = len(self._tracks)
        self._tracks.clear()
        return removed_count

    def preview(self, limit: int = 10) -> tuple[Track, ...]:
        if limit < 0:
            raise ValueError("limit cannot be negative")
        return tuple(list(self._tracks)[:limit])

    def extend(self, tracks: Iterable[Track]) -> None:
        for track in tracks:
            self.enqueue(track)

    def _validate_index(self, index: int) -> None:
        if index < 0 or index >= len(self._tracks):
            raise QueuePositionError("Queue position is outside the available range")
