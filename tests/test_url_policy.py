import unittest

from discord_music_bot.adapters.media.yt_dlp_resolver import _is_spotify_track_url, _is_youtube_url


class UrlPolicyTests(unittest.TestCase):
    def test_youtube_allowlist(self) -> None:
        self.assertTrue(_is_youtube_url("https://www.youtube.com/watch?v=abc"))
        self.assertTrue(_is_youtube_url("youtu.be/abc"))
        self.assertFalse(_is_youtube_url("https://youtube.com.evil.example/watch?v=abc"))

    def test_spotify_requires_https_track_url(self) -> None:
        self.assertTrue(_is_spotify_track_url("https://open.spotify.com/track/abc"))
        self.assertFalse(_is_spotify_track_url("http://open.spotify.com/track/abc"))
        self.assertFalse(_is_spotify_track_url("https://open.spotify.com/playlist/abc"))
