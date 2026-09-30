from __future__ import annotations

import asyncio

from discord_music_bot.domain import GuildQueue, QueueFullError, QueuePositionError, Track

from .ports import TrackResolver


class MusicService:
    """Application service that owns isolated queue state for each Discord guild."""

    def __init__(self, resolver: TrackResolver, max_queue_size: int, max_query_length: int) -> None:
        self._resolver = resolver
        self._max_queue_size = max_queue_size
        self._max_query_length = max_query_length
        self._queues: dict[int, GuildQueue] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def lock_for(self, guild_id: int) -> asyncio.Lock:
        return self._locks.setdefault(guild_id, asyncio.Lock())

    def queue_for(self, guild_id: int) -> GuildQueue:
        return self._queues.setdefault(guild_id, GuildQueue(self._max_queue_size))

    async def enqueue(self, guild_id: int, query: str, requested_by: int) -> Track:
        normalized = " ".join(query.split())
        if not normalized:
            raise ValueError("Query lagu tidak boleh kosong.")
        if len(normalized) > self._max_query_length:
            raise ValueError(f"Query maksimal {self._max_query_length} karakter.")

        async with self.lock_for(guild_id):
            if self.queue_for(guild_id).is_full:
                raise QueueFullError(f"Queue limit of {self._max_queue_size} tracks reached")

        track = await self._resolver.resolve(normalized, requested_by)
        async with self.lock_for(guild_id):
            self.queue_for(guild_id).enqueue(track)
        return track

    async def pop_next(self, guild_id: int) -> Track | None:
        async with self.lock_for(guild_id):
            return self.queue_for(guild_id).dequeue()

    async def next_for_playback(self, guild_id: int) -> Track | None:
        """Remove the next track and refresh its provider URL just before playback."""
        track = await self.pop_next(guild_id)
        if track is None:
            return None
        return await self._resolver.refresh(track)

    async def refresh_track(self, track: Track) -> Track:
        """Refresh an already selected track without changing any guild queue."""
        return await self._resolver.refresh(track)

    async def requeue(self, guild_id: int, track: Track) -> None:
        """Append a completed track for queue-loop mode under the guild lock."""
        async with self.lock_for(guild_id):
            self.queue_for(guild_id).enqueue(track)

    async def remove(self, guild_id: int, position: int) -> Track:
        async with self.lock_for(guild_id):
            return self.queue_for(guild_id).remove(self._index_for(position))

    async def move(self, guild_id: int, source_position: int, destination_position: int) -> Track:
        async with self.lock_for(guild_id):
            return self.queue_for(guild_id).move(
                self._index_for(source_position),
                self._index_for(destination_position),
            )

    async def shuffle(self, guild_id: int) -> int:
        async with self.lock_for(guild_id):
            return self.queue_for(guild_id).shuffle()

    async def clear(self, guild_id: int) -> int:
        async with self.lock_for(guild_id):
            return self.queue_for(guild_id).clear()

    def preview(self, guild_id: int, limit: int = 10) -> tuple[Track, ...]:
        return self.queue_for(guild_id).preview(limit)

    def remove_guild(self, guild_id: int) -> None:
        self._queues.pop(guild_id, None)
        self._locks.pop(guild_id, None)

    @staticmethod
    def _index_for(position: int) -> int:
        if position < 1:
            raise QueuePositionError("Queue positions start at 1")
        return position - 1


__all__ = ["MusicService", "QueueFullError", "QueuePositionError"]
