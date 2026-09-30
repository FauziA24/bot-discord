from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class GuildSettings:
    dj_role_id: int | None = None
    command_channel_id: int | None = None


class GuildSettingsService:
    """Owns guild-scoped configuration until a repository port is added in BOT-201."""

    def __init__(self) -> None:
        self._settings: dict[int, GuildSettings] = {}

    def get(self, guild_id: int) -> GuildSettings:
        return self._settings.get(guild_id, GuildSettings())

    def set_dj_role(self, guild_id: int, role_id: int) -> GuildSettings:
        updated = replace(self.get(guild_id), dj_role_id=role_id)
        self._settings[guild_id] = updated
        return updated

    def set_command_channel(self, guild_id: int, channel_id: int) -> GuildSettings:
        updated = replace(self.get(guild_id), command_channel_id=channel_id)
        self._settings[guild_id] = updated
        return updated

    def reset(self, guild_id: int) -> None:
        self._settings.pop(guild_id, None)

    def remove_guild(self, guild_id: int) -> None:
        self._settings.pop(guild_id, None)
