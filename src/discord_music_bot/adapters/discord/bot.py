from __future__ import annotations

import logging
import shutil

import discord
from discord.ext import commands

from discord_music_bot.application import GuildSettingsService, MusicService
from discord_music_bot.config import ConfigurationError, Settings

from ..media import YtDlpTrackResolver
from .music_cog import MusicCog
from .player import PlayerRegistry

LOGGER = logging.getLogger(__name__)


class MusicBot(commands.Bot):
    def __init__(
        self,
        settings: Settings,
        music_service: MusicService,
        guild_settings: GuildSettingsService,
        ffmpeg_path: str,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(
            command_prefix=settings.command_prefix,
            intents=intents,
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.settings = settings
        self.music_service = music_service
        self.guild_settings = guild_settings
        self.players = PlayerRegistry(
            self,
            music_service,
            ffmpeg_path,
            settings.idle_disconnect_seconds,
            guild_settings,
        )

    async def setup_hook(self) -> None:
        await self.add_cog(MusicCog(self.music_service, self.players, self.guild_settings))
        if self.settings.sync_commands:
            synced = await self.tree.sync()
            LOGGER.info("Synced %d application commands", len(synced))

    async def on_ready(self) -> None:
        LOGGER.info("Bot online as %s (%s)", self.user, getattr(self.user, "id", "unknown"))

    async def on_member_join(self, member: discord.Member) -> None:
        channel = discord.utils.get(member.guild.text_channels, name="welcome")
        channel = channel or discord.utils.get(member.guild.text_channels, name="general")
        if channel is None:
            channel = next(
                (
                    candidate
                    for candidate in member.guild.text_channels
                    if candidate.permissions_for(member.guild.me).send_messages
                ),
                None,
            )
        if channel and channel.permissions_for(member.guild.me).send_messages:
            try:
                await channel.send(
                    f"👋 Selamat datang, {member.mention}! Nikmati server ini.",
                    allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
                )
            except (discord.HTTPException, discord.Forbidden):
                LOGGER.exception("Failed to send welcome message in guild %s", member.guild.id)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        await self.players.remove(guild.id)


def create_bot(settings: Settings) -> MusicBot:
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise ConfigurationError("FFmpeg tidak ditemukan di PATH.")
    resolver = YtDlpTrackResolver(settings.spotify_client_id, settings.spotify_client_secret)
    service = MusicService(resolver, settings.max_queue_size, settings.max_query_length)
    guild_settings = GuildSettingsService()
    return MusicBot(settings, service, guild_settings, ffmpeg_path)
