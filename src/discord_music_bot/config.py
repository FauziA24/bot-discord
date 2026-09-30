from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(ValueError):
    """Raised when required runtime configuration is missing or invalid."""


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    discord_token: str
    command_prefix: str = "!"
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    max_queue_size: int = 100
    max_query_length: int = 300
    idle_disconnect_seconds: int = 30
    sync_commands: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token or token == "your_discord_bot_token_here":
            raise ConfigurationError("DISCORD_TOKEN belum diisi dengan token bot yang valid.")

        prefix = os.getenv("COMMAND_PREFIX", "!").strip()
        if not prefix or len(prefix) > 5:
            raise ConfigurationError("COMMAND_PREFIX harus terdiri dari 1-5 karakter.")

        try:
            max_queue_size = int(os.getenv("MAX_QUEUE_SIZE", "100"))
            max_query_length = int(os.getenv("MAX_QUERY_LENGTH", "300"))
            idle_disconnect_seconds = int(os.getenv("IDLE_DISCONNECT_SECONDS", "30"))
        except ValueError as exc:
            raise ConfigurationError("Konfigurasi batas numerik harus berupa integer.") from exc

        if not 1 <= max_queue_size <= 1000:
            raise ConfigurationError("MAX_QUEUE_SIZE harus berada di antara 1 dan 1000.")
        if not 20 <= max_query_length <= 2000:
            raise ConfigurationError("MAX_QUERY_LENGTH harus berada di antara 20 dan 2000.")
        if not 0 <= idle_disconnect_seconds <= 3600:
            raise ConfigurationError("IDLE_DISCONNECT_SECONDS harus berada di antara 0 dan 3600.")

        spotify_id = os.getenv("SPOTIPY_CLIENT_ID") or None
        spotify_secret = os.getenv("SPOTIPY_CLIENT_SECRET") or None
        if bool(spotify_id) != bool(spotify_secret):
            raise ConfigurationError("SPOTIPY_CLIENT_ID dan SPOTIPY_CLIENT_SECRET harus diisi bersamaan.")

        return cls(
            discord_token=token,
            command_prefix=prefix,
            spotify_client_id=spotify_id,
            spotify_client_secret=spotify_secret,
            max_queue_size=max_queue_size,
            max_query_length=max_query_length,
            idle_disconnect_seconds=idle_disconnect_seconds,
            sync_commands=_as_bool(os.getenv("SYNC_COMMANDS")),
        )
