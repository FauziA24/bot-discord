import unittest

from discord_music_bot.application import GuildSettingsService


class GuildSettingsServiceTests(unittest.TestCase):
    def test_defaults_are_safe_and_unrestricted(self) -> None:
        service = GuildSettingsService()

        settings = service.get(1)

        self.assertIsNone(settings.dj_role_id)
        self.assertIsNone(settings.command_channel_id)

    def test_settings_are_isolated_per_guild(self) -> None:
        service = GuildSettingsService()
        service.set_dj_role(1, 100)
        service.set_command_channel(1, 200)
        service.set_dj_role(2, 300)

        self.assertEqual(service.get(1).dj_role_id, 100)
        self.assertEqual(service.get(1).command_channel_id, 200)
        self.assertEqual(service.get(2).dj_role_id, 300)
        self.assertIsNone(service.get(2).command_channel_id)

    def test_reset_only_affects_target_guild(self) -> None:
        service = GuildSettingsService()
        service.set_dj_role(1, 100)
        service.set_dj_role(2, 200)

        service.reset(1)

        self.assertIsNone(service.get(1).dj_role_id)
        self.assertEqual(service.get(2).dj_role_id, 200)
