import os
import unittest
from unittest.mock import patch

from discord_music_bot.config import ConfigurationError, Settings


class SettingsTests(unittest.TestCase):
    def test_requires_real_token(self) -> None:
        with patch.dict(os.environ, {"DISCORD_TOKEN": "your_discord_bot_token_here"}, clear=True):
            with self.assertRaises(ConfigurationError):
                Settings.from_env()

    def test_spotify_credentials_must_be_paired(self) -> None:
        with patch.dict(
            os.environ,
            {"DISCORD_TOKEN": "test-token", "SPOTIPY_CLIENT_ID": "client"},
            clear=True,
        ):
            with self.assertRaises(ConfigurationError):
                Settings.from_env()

    def test_valid_values_are_loaded(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "test-token",
                "MAX_QUEUE_SIZE": "25",
                "SYNC_COMMANDS": "true",
            },
            clear=True,
        ):
            settings = Settings.from_env()

        self.assertEqual(settings.max_queue_size, 25)
        self.assertTrue(settings.sync_commands)
