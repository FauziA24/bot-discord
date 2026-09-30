import unittest

from discord_music_bot.application import MusicService
from discord_music_bot.domain import QueueFullError, QueuePositionError, Track


class FakeResolver:
    def __init__(self) -> None:
        self.calls = 0
        self.refresh_calls = 0

    async def resolve(self, query: str, requested_by: int) -> Track:
        self.calls += 1
        return Track(
            query,
            f"https://stale-stream/{query}",
            requested_by,
            query,
            webpage_url=f"https://www.youtube.com/watch?v={query}",
        )

    async def refresh(self, track: Track) -> Track:
        self.refresh_calls += 1
        return Track(
            track.title,
            f"https://fresh-stream/{self.refresh_calls}",
            track.requested_by,
            track.original_query,
            webpage_url=track.webpage_url,
        )


class MusicServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_queues_are_isolated_per_guild(self) -> None:
        service = MusicService(FakeResolver(), max_queue_size=5, max_query_length=50)
        await service.enqueue(1, "guild one", 10)
        await service.enqueue(2, "guild two", 20)

        self.assertEqual((await service.pop_next(1)).title, "guild one")
        self.assertEqual((await service.pop_next(2)).title, "guild two")

    async def test_query_is_normalized_and_limited(self) -> None:
        service = MusicService(FakeResolver(), max_queue_size=5, max_query_length=20)
        result = await service.enqueue(1, "  one   two  ", 10)
        self.assertEqual(result.title, "one two")

        with self.assertRaises(ValueError):
            await service.enqueue(1, "x" * 21, 10)

    async def test_clear_only_affects_target_guild(self) -> None:
        service = MusicService(FakeResolver(), max_queue_size=5, max_query_length=50)
        await service.enqueue(1, "first", 10)
        await service.enqueue(2, "second", 20)
        await service.clear(1)

        self.assertIsNone(await service.pop_next(1))
        self.assertEqual((await service.pop_next(2)).title, "second")

    async def test_full_queue_rejects_before_media_resolution(self) -> None:
        resolver = FakeResolver()
        service = MusicService(resolver, max_queue_size=1, max_query_length=50)
        await service.enqueue(1, "first", 10)

        with self.assertRaises(QueueFullError):
            await service.enqueue(1, "second", 10)

        self.assertEqual(resolver.calls, 1)

    async def test_next_for_playback_refreshes_expiring_stream_url(self) -> None:
        resolver = FakeResolver()
        service = MusicService(resolver, max_queue_size=5, max_query_length=50)
        queued = await service.enqueue(1, "long wait", 10)

        playable = await service.next_for_playback(1)

        self.assertEqual(queued.stream_url, "https://stale-stream/long wait")
        self.assertEqual(playable.stream_url, "https://fresh-stream/1")
        self.assertEqual(playable.original_query, queued.original_query)
        self.assertEqual(playable.requested_by, queued.requested_by)
        self.assertEqual(resolver.refresh_calls, 1)
        self.assertIsNone(await service.next_for_playback(1))

    async def test_queue_mutations_are_isolated_and_use_one_based_positions(self) -> None:
        service = MusicService(FakeResolver(), max_queue_size=5, max_query_length=50)
        for title in ("first", "second", "third"):
            await service.enqueue(1, title, 10)
        await service.enqueue(2, "other guild", 20)

        removed = await service.remove(1, 2)
        moved = await service.move(1, 2, 1)

        self.assertEqual(removed.title, "second")
        self.assertEqual(moved.title, "third")
        self.assertEqual([item.title for item in service.preview(1)], ["third", "first"])
        self.assertEqual([item.title for item in service.preview(2)], ["other guild"])

    async def test_invalid_user_position_does_not_modify_queue(self) -> None:
        service = MusicService(FakeResolver(), max_queue_size=5, max_query_length=50)
        await service.enqueue(1, "first", 10)

        with self.assertRaises(QueuePositionError):
            await service.remove(1, 0)

        self.assertEqual([item.title for item in service.preview(1)], ["first"])

    async def test_clear_only_removes_target_guild_and_returns_count(self) -> None:
        service = MusicService(FakeResolver(), max_queue_size=5, max_query_length=50)
        await service.enqueue(1, "first", 10)
        await service.enqueue(1, "second", 10)
        await service.enqueue(2, "other guild", 20)

        self.assertEqual(await service.clear(1), 2)
        self.assertEqual([item.title for item in service.preview(2)], ["other guild"])

    async def test_requeue_appends_completed_track_only_to_target_guild(self) -> None:
        service = MusicService(FakeResolver(), max_queue_size=5, max_query_length=50)
        completed = Track("completed", "https://expired", 10, "completed")
        await service.enqueue(1, "next", 10)
        await service.enqueue(2, "other guild", 20)

        await service.requeue(1, completed)

        self.assertEqual([item.title for item in service.preview(1)], ["next", "completed"])
        self.assertEqual([item.title for item in service.preview(2)], ["other guild"])
