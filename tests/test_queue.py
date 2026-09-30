import random
import unittest

from discord_music_bot.domain import GuildQueue, QueueFullError, QueuePositionError, Track


def track(title: str) -> Track:
    return Track(title=title, stream_url=f"https://stream/{title}", requested_by=1, original_query=title)


class GuildQueueTests(unittest.TestCase):
    def test_queue_is_fifo(self) -> None:
        queue = GuildQueue(max_size=3)
        queue.enqueue(track("first"))
        queue.enqueue(track("second"))

        self.assertEqual(queue.dequeue().title, "first")
        self.assertEqual(queue.dequeue().title, "second")
        self.assertIsNone(queue.dequeue())

    def test_queue_enforces_capacity(self) -> None:
        queue = GuildQueue(max_size=1)
        self.assertFalse(queue.is_full)
        queue.enqueue(track("first"))
        self.assertTrue(queue.is_full)

        with self.assertRaises(QueueFullError):
            queue.enqueue(track("second"))

    def test_preview_does_not_consume_tracks(self) -> None:
        queue = GuildQueue(max_size=3)
        queue.extend([track("first"), track("second")])

        self.assertEqual([item.title for item in queue.preview(1)], ["first"])
        self.assertEqual(len(queue), 2)

    def test_remove_and_move_use_atomic_queue_positions(self) -> None:
        queue = GuildQueue(max_size=4)
        queue.extend([track("first"), track("second"), track("third")])

        removed = queue.remove(1)
        moved = queue.move(1, 0)

        self.assertEqual(removed.title, "second")
        self.assertEqual(moved.title, "third")
        self.assertEqual([item.title for item in queue.preview()], ["third", "first"])

    def test_invalid_positions_do_not_modify_queue(self) -> None:
        queue = GuildQueue(max_size=3)
        queue.extend([track("first"), track("second")])

        with self.assertRaises(QueuePositionError):
            queue.remove(2)
        with self.assertRaises(QueuePositionError):
            queue.move(0, -1)

        self.assertEqual([item.title for item in queue.preview()], ["first", "second"])

    def test_shuffle_is_deterministic_with_injected_rng_and_preserves_items(self) -> None:
        queue = GuildQueue(max_size=4)
        queue.extend([track("first"), track("second"), track("third"), track("fourth")])

        count = queue.shuffle(random.Random(7))

        self.assertEqual(count, 4)
        self.assertEqual(
            [item.title for item in queue.preview()],
            ["fourth", "second", "first", "third"],
        )

    def test_clear_returns_removed_count(self) -> None:
        queue = GuildQueue(max_size=3)
        queue.extend([track("first"), track("second")])

        self.assertEqual(queue.clear(), 2)
        self.assertEqual(queue.clear(), 0)
