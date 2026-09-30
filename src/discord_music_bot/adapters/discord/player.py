from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

import discord

from discord_music_bot.application import GuildSettingsService, MediaResolutionError, MusicService
from discord_music_bot.domain import LoopMode, QueueFullError, Track

from .authorization import has_control_permission, is_same_voice_channel

LOGGER = logging.getLogger(__name__)
FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
FFMPEG_OPTIONS = "-vn"


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "?:??"
    minutes, remaining = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{remaining:02d}" if hours else f"{minutes}:{remaining:02d}"


def _now_playing_embed(track: Track, elapsed_seconds: int = 0) -> discord.Embed:
    duration = track.duration_seconds
    ratio = min(1.0, elapsed_seconds / duration) if duration and duration > 0 else 0.0
    completed = round(ratio * 12)
    bar = "▰" * completed + "▱" * (12 - completed)
    progress = f"{bar}  `{_format_duration(elapsed_seconds)} / {_format_duration(duration)}`"
    embed = discord.Embed(title="🎵 Sekarang memutar", description=track.safe_title, color=discord.Color.blue())
    embed.add_field(name="Progress", value=progress, inline=False)
    return embed


class NowPlayingControls(discord.ui.View):
    def __init__(self, player: GuildPlayer) -> None:
        super().__init__(timeout=3600)
        self.player = player

    async def _authorized(self, interaction: discord.Interaction, *, allow_requester: bool) -> bool:
        member = interaction.user
        guild = interaction.guild
        voice = guild.voice_client if guild else None
        if not isinstance(member, discord.Member) or not is_same_voice_channel(member, voice):
            await interaction.response.send_message(
                "⚠️ Anda harus berada di voice channel yang sama dengan bot.", ephemeral=True
            )
            return False
        requester_id = self.player.current_track.requested_by if self.player.current_track else None
        dj_role_id = self.player.guild_settings.get(self.player.guild_id).dj_role_id
        if not has_control_permission(
            member,
            requester_id,
            allow_requester=allow_requester,
            dj_role_id=dj_role_id,
        ):
            await interaction.response.send_message("⛔ Anda tidak memiliki izin kontrol musik.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Pause", emoji="⏸️", style=discord.ButtonStyle.secondary)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if await self._authorized(interaction, allow_requester=True):
            message = "⏸️ Musik dijeda." if self.player.pause() else "⚠️ Musik tidak sedang diputar."
            await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(label="Resume", emoji="▶️", style=discord.ButtonStyle.success)
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if await self._authorized(interaction, allow_requester=True):
            message = "▶️ Musik dilanjutkan." if self.player.resume() else "⚠️ Musik tidak sedang dijeda."
            await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.primary)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if await self._authorized(interaction, allow_requester=True):
            message = "⏭️ Lagu dilewati." if await self.player.skip() else "⚠️ Tidak ada lagu aktif."
            await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if await self._authorized(interaction, allow_requester=False):
            await self.player.stop()
            await interaction.response.send_message("⏹️ Musik dihentikan dan antrean dikosongkan.", ephemeral=True)
            self.stop()


class GuildPlayer:
    def __init__(
        self,
        bot: discord.Client,
        guild_id: int,
        music_service: MusicService,
        ffmpeg_path: str,
        idle_disconnect_seconds: int,
        guild_settings: GuildSettingsService | None = None,
    ) -> None:
        self.bot = bot
        self.guild_id = guild_id
        self.music_service = music_service
        self.ffmpeg_path = ffmpeg_path
        self.idle_disconnect_seconds = idle_disconnect_seconds
        self.guild_settings = guild_settings or GuildSettingsService()
        self.current_track: Track | None = None
        self.loop_mode = LoopMode.OFF
        self.notification_channel_id: int | None = None
        self._transition_lock = asyncio.Lock()
        self._idle_task: asyncio.Task[None] | None = None
        self._manual_advance = False
        self._controls: NowPlayingControls | None = None

    def _voice_client(self) -> discord.VoiceClient | None:
        guild = self.bot.get_guild(self.guild_id)
        return guild.voice_client if guild else None

    async def start_if_idle(self, notification_channel_id: int) -> None:
        self.notification_channel_id = notification_channel_id
        voice = self._voice_client()
        if voice and not voice.is_playing() and not voice.is_paused():
            await self._play_next()

    async def _play_next(self, repeat_track: Track | None = None) -> None:
        async with self._transition_lock:
            voice = self._voice_client()
            if not voice or not voice.is_connected() or voice.is_playing() or voice.is_paused():
                return

            while True:
                try:
                    if repeat_track is not None:
                        track = await self.music_service.refresh_track(repeat_track)
                        repeat_track = None
                    else:
                        track = await self.music_service.next_for_playback(self.guild_id)
                except MediaResolutionError:
                    LOGGER.warning("Queued media refresh failed in guild %s", self.guild_id)
                    await self._notify("⚠️ Satu lagu dilewati karena sumber medianya tidak dapat diperbarui.")
                    repeat_track = None
                    continue

                if track is None:
                    self.current_track = None
                    self._schedule_idle_disconnect()
                    return
                break

            self._cancel_idle_disconnect()
            self.current_track = track
            source = discord.FFmpegPCMAudio(
                track.stream_url,
                executable=self.ffmpeg_path,
                before_options=FFMPEG_BEFORE_OPTIONS,
                options=FFMPEG_OPTIONS,
            )
            voice.play(source, after=self._after_playback)
            await self._notify_now_playing(track)

    def _after_playback(self, error: Exception | None) -> None:
        future = asyncio.run_coroutine_threadsafe(self._handle_playback_end(error), self.bot.loop)

        def log_failure(completed: object) -> None:
            with suppress(Exception):
                exception = future.exception()
                if exception:
                    LOGGER.error("Playback transition failed", exc_info=exception)

        future.add_done_callback(log_failure)

    async def _handle_playback_end(self, error: Exception | None) -> None:
        completed_track = self.current_track
        manual_advance = self._manual_advance
        self._manual_advance = False
        if error:
            LOGGER.error("Discord audio player error: %s", error)
        self.current_track = None

        if not error and not manual_advance and completed_track:
            if self.loop_mode is LoopMode.TRACK:
                await self._play_next(completed_track)
                return
            if self.loop_mode is LoopMode.QUEUE:
                try:
                    await self.music_service.requeue(self.guild_id, completed_track)
                except QueueFullError:
                    LOGGER.warning("Could not requeue looped track in full guild queue %s", self.guild_id)
                    await self._notify("⚠️ Track selesai tidak dapat diulang karena antrean penuh.")
        await self._play_next()

    async def skip(self) -> bool:
        voice = self._voice_client()
        if not voice or (not voice.is_playing() and not voice.is_paused()):
            return False
        self._manual_advance = True
        voice.stop()
        return True

    async def stop(self) -> None:
        self._manual_advance = True
        self.loop_mode = LoopMode.OFF
        self._stop_controls()
        await self.music_service.clear(self.guild_id)
        voice = self._voice_client()
        if voice and (voice.is_playing() or voice.is_paused()):
            voice.stop()
        self.current_track = None

    async def leave(self) -> None:
        self._cancel_idle_disconnect()
        self._manual_advance = True
        self.loop_mode = LoopMode.OFF
        self._stop_controls()
        await self.music_service.clear(self.guild_id)
        voice = self._voice_client()
        if voice and voice.is_connected():
            await voice.disconnect(force=True)
        self.current_track = None

    def set_loop_mode(self, mode: LoopMode) -> LoopMode:
        self.loop_mode = mode
        return mode

    def pause(self) -> bool:
        voice = self._voice_client()
        if not voice or not voice.is_playing():
            return False
        voice.pause()
        return True

    def resume(self) -> bool:
        voice = self._voice_client()
        if not voice or not voice.is_paused():
            return False
        voice.resume()
        return True

    async def _notify(self, message: str) -> None:
        if self.notification_channel_id is None:
            return
        channel = self.bot.get_channel(self.notification_channel_id)
        if isinstance(channel, discord.abc.Messageable):
            with suppress(discord.HTTPException, discord.Forbidden):
                await channel.send(message, allowed_mentions=discord.AllowedMentions.none())

    async def _notify_now_playing(self, track: Track) -> None:
        self._stop_controls()
        if self.notification_channel_id is None:
            return
        channel = self.bot.get_channel(self.notification_channel_id)
        if isinstance(channel, discord.abc.Messageable):
            self._controls = NowPlayingControls(self)
            with suppress(discord.HTTPException, discord.Forbidden):
                await channel.send(
                    embed=_now_playing_embed(track),
                    view=self._controls,
                    allowed_mentions=discord.AllowedMentions.none(),
                )

    def _stop_controls(self) -> None:
        if self._controls:
            self._controls.stop()
        self._controls = None

    def _schedule_idle_disconnect(self) -> None:
        self._cancel_idle_disconnect()
        if self.idle_disconnect_seconds <= 0:
            return
        self._idle_task = asyncio.create_task(self._disconnect_when_idle())

    def _cancel_idle_disconnect(self) -> None:
        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()
        self._idle_task = None

    async def _disconnect_when_idle(self) -> None:
        try:
            await asyncio.sleep(self.idle_disconnect_seconds)
            voice = self._voice_client()
            queue_empty = not self.music_service.preview(self.guild_id, 1)
            if voice and voice.is_connected() and not voice.is_playing() and queue_empty:
                await voice.disconnect()
        except asyncio.CancelledError:
            raise


class PlayerRegistry:
    def __init__(
        self,
        bot: discord.Client,
        music_service: MusicService,
        ffmpeg_path: str,
        idle_disconnect_seconds: int,
        guild_settings: GuildSettingsService | None = None,
    ) -> None:
        self._bot = bot
        self._music_service = music_service
        self._ffmpeg_path = ffmpeg_path
        self._idle_disconnect_seconds = idle_disconnect_seconds
        self._guild_settings = guild_settings or GuildSettingsService()
        self._players: dict[int, GuildPlayer] = {}

    def get(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self._players:
            self._players[guild_id] = GuildPlayer(
                self._bot,
                guild_id,
                self._music_service,
                self._ffmpeg_path,
                self._idle_disconnect_seconds,
                self._guild_settings,
            )
        return self._players[guild_id]

    async def remove(self, guild_id: int) -> None:
        player = self._players.pop(guild_id, None)
        if player:
            await player.leave()
        self._music_service.remove_guild(guild_id)
        self._guild_settings.remove_guild(guild_id)
