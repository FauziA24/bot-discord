import unittest
from unittest.mock import patch

from discord_music_bot.adapters.discord.player import GuildPlayer, _format_duration, _now_playing_embed
from discord_music_bot.application import MediaResolutionError
from discord_music_bot.domain import LoopMode, Track


class FakeVoiceClient:
    def __init__(self) -> None:
        self.source = None

    def is_connected(self) -> bool:
        return True

    def is_playing(self) -> bool:
        return False

    def is_paused(self) -> bool:
        return False

    def play(self, source: object, *, after: object) -> None:
        self.source = source


class FakeBot:
    def __init__(self, voice: FakeVoiceClient) -> None:
        self._guild = type("Guild", (), {"voice_client": voice})()

    def get_guild(self, guild_id: int) -> object:
        return self._guild

    def get_channel(self, channel_id: int) -> None:
        return None


class FakePlaybackService:
    def __init__(self, results: list[Track | Exception]) -> None:
        self.results = results
        self.calls = 0
        self.refresh_calls = 0
        self.requeued: list[Track] = []

    async def next_for_playback(self, guild_id: int) -> Track | None:
        self.calls += 1
        result = self.results.pop(0) if self.results else None
        if isinstance(result, Exception):
            raise result
        return result

    async def refresh_track(self, track: Track) -> Track:
        self.refresh_calls += 1
        return Track(
            track.title,
            f"https://repeat-stream/{self.refresh_calls}",
            track.requested_by,
            track.original_query,
        )

    async def requeue(self, guild_id: int, track: Track) -> None:
        self.requeued.append(track)

    async def clear(self, guild_id: int) -> int:
        count = len(self.results)
        self.results.clear()
        return count


class GuildPlayerTests(unittest.IsolatedAsyncioTestCase):
    async def test_player_uses_freshly_resolved_stream_url(self) -> None:
        voice = FakeVoiceClient()
        service = FakePlaybackService(
            [Track("title", "https://fresh-stream/1", 10, "query")]
        )
        player = GuildPlayer(FakeBot(voice), 1, service, "ffmpeg", 0)

        with patch("discord_music_bot.adapters.discord.player.discord.FFmpegPCMAudio") as audio:
            await player.start_if_idle(99)

        audio.assert_called_once()
        self.assertEqual(audio.call_args.args[0], "https://fresh-stream/1")
        self.assertEqual(service.calls, 1)

    async def test_player_skips_track_when_refresh_fails(self) -> None:
        voice = FakeVoiceClient()
        service = FakePlaybackService(
            [
                MediaResolutionError("safe failure"),
                Track("next", "https://fresh-stream/2", 10, "query"),
            ]
        )
        player = GuildPlayer(FakeBot(voice), 1, service, "ffmpeg", 0)

        with patch("discord_music_bot.adapters.discord.player.discord.FFmpegPCMAudio") as audio:
            await player.start_if_idle(99)

        self.assertEqual(audio.call_args.args[0], "https://fresh-stream/2")
        self.assertEqual(service.calls, 2)

    async def test_track_loop_refreshes_and_replays_completed_track(self) -> None:
        voice = FakeVoiceClient()
        service = FakePlaybackService([Track("first", "https://stream/1", 10, "query")])
        player = GuildPlayer(FakeBot(voice), 1, service, "ffmpeg", 0)
        player.set_loop_mode(LoopMode.TRACK)

        with patch("discord_music_bot.adapters.discord.player.discord.FFmpegPCMAudio") as audio:
            await player.start_if_idle(99)
            await player._handle_playback_end(None)

        self.assertEqual(service.refresh_calls, 1)
        self.assertEqual(audio.call_args.args[0], "https://repeat-stream/1")
        self.assertEqual(player.current_track.title, "first")

    async def test_queue_loop_requeues_completed_track_then_plays_next(self) -> None:
        voice = FakeVoiceClient()
        first = Track("first", "https://stream/1", 10, "first")
        second = Track("second", "https://stream/2", 20, "second")
        service = FakePlaybackService([first, second])
        player = GuildPlayer(FakeBot(voice), 1, service, "ffmpeg", 0)
        player.set_loop_mode(LoopMode.QUEUE)

        with patch("discord_music_bot.adapters.discord.player.discord.FFmpegPCMAudio"):
            await player.start_if_idle(99)
            await player._handle_playback_end(None)

        self.assertEqual(service.requeued, [first])
        self.assertEqual(player.current_track, second)

    async def test_manual_advance_does_not_repeat_track(self) -> None:
        voice = FakeVoiceClient()
        first = Track("first", "https://stream/1", 10, "first")
        second = Track("second", "https://stream/2", 20, "second")
        service = FakePlaybackService([first, second])
        player = GuildPlayer(FakeBot(voice), 1, service, "ffmpeg", 0)
        player.set_loop_mode(LoopMode.TRACK)

        with patch("discord_music_bot.adapters.discord.player.discord.FFmpegPCMAudio"):
            await player.start_if_idle(99)
            player._manual_advance = True
            await player._handle_playback_end(None)

        self.assertEqual(service.refresh_calls, 0)
        self.assertEqual(player.current_track, second)

    async def test_stop_resets_loop_mode(self) -> None:
        voice = FakeVoiceClient()
        service = FakePlaybackService([])
        player = GuildPlayer(FakeBot(voice), 1, service, "ffmpeg", 0)
        player.set_loop_mode(LoopMode.QUEUE)

        await player.stop()

        self.assertIs(player.loop_mode, LoopMode.OFF)


class NowPlayingPresentationTests(unittest.TestCase):
    def test_duration_format_supports_minutes_and_hours(self) -> None:
        self.assertEqual(_format_duration(65), "1:05")
        self.assertEqual(_format_duration(3661), "1:01:01")
        self.assertEqual(_format_duration(None), "?:??")

    def test_embed_has_sanitized_title_and_progress(self) -> None:
        track = Track("  unsafe   title  ", "https://stream", 1, "query", duration_seconds=200)

        embed = _now_playing_embed(track, elapsed_seconds=50)

        self.assertEqual(embed.description, "unsafe title")
        self.assertEqual(embed.fields[0].name, "Progress")
        self.assertIn("0:50 / 3:20", embed.fields[0].value)


if __name__ == "__main__":
    unittest.main()
