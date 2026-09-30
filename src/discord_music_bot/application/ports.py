from __future__ import annotations

from typing import Protocol

from discord_music_bot.domain import Track


class MediaResolutionError(RuntimeError):
    """Safe, user-facing error produced while resolving a media query."""


class TrackResolver(Protocol):
    async def resolve(self, query: str, requested_by: int) -> Track:
        """Resolve a user query into a playable track."""

    async def refresh(self, track: Track) -> Track:
        """Return the track with a newly resolved, short-lived stream URL."""
