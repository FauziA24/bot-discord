from __future__ import annotations

import logging
from contextlib import suppress

import discord
from discord.ext import commands

from discord_music_bot.application import GuildSettingsService, MediaResolutionError, MusicService, QueuePositionError
from discord_music_bot.domain import LoopMode, QueueFullError

from .authorization import has_control_permission, is_same_voice_channel
from .player import GuildPlayer, PlayerRegistry

LOGGER = logging.getLogger(__name__)


class MusicCog(commands.Cog):
    def __init__(
        self,
        music_service: MusicService,
        players: PlayerRegistry,
        guild_settings: GuildSettingsService | None = None,
    ) -> None:
        self.music_service = music_service
        self.players = players
        self.guild_settings = guild_settings or GuildSettingsService()

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.guild is None or ctx.command is None:
            return True
        if ctx.command.name in {"setdjrole", "setmusicchannel", "resetmusicconfig", "musicconfig"}:
            return True
        channel_id = self.guild_settings.get(ctx.guild.id).command_channel_id
        return channel_id is None or ctx.channel.id == channel_id

    @staticmethod
    def _author_voice_channel(ctx: commands.Context) -> discord.VoiceChannel | discord.StageChannel | None:
        author = ctx.author
        if isinstance(author, discord.Member) and author.voice:
            return author.voice.channel
        return None

    async def _connect_or_validate(self, ctx: commands.Context) -> discord.VoiceClient | None:
        channel = self._author_voice_channel(ctx)
        if channel is None:
            await ctx.reply("⚠️ Masuk ke voice channel terlebih dahulu.")
            return None

        voice = ctx.voice_client
        if voice and voice.channel != channel:
            await ctx.reply("⚠️ Bot sedang digunakan di voice channel lain.")
            return None
        if voice is None:
            try:
                voice = await channel.connect(self_deaf=True)
            except (discord.ClientException, discord.Forbidden, discord.HTTPException):
                LOGGER.exception("Failed to connect to voice channel")
                await ctx.reply("❌ Bot tidak dapat masuk ke voice channel tersebut.")
                return None
        return voice

    async def _can_control(
        self,
        ctx: commands.Context,
        player: GuildPlayer,
        *,
        allow_requester: bool,
    ) -> bool:
        author = ctx.author
        if not isinstance(author, discord.Member) or not is_same_voice_channel(author, ctx.voice_client):
            await ctx.reply("⚠️ Anda harus berada di voice channel yang sama dengan bot.")
            return False

        requester_id = player.current_track.requested_by if player.current_track else None
        dj_role_id = self.guild_settings.get(ctx.guild.id).dj_role_id if ctx.guild else None
        if has_control_permission(
            author,
            requester_id,
            allow_requester=allow_requester,
            dj_role_id=dj_role_id,
        ):
            return True

        await ctx.reply("⛔ Command ini memerlukan role `DJ`, izin Manage Server/Move Members, atau requester lagu.")
        return False

    @commands.hybrid_command(name="play", description="Putar lagu dari pencarian, YouTube, atau track Spotify.")
    @commands.guild_only()
    @commands.cooldown(2, 10, commands.BucketType.user)
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        """Resolve and enqueue one track in the current guild."""
        was_connected = ctx.voice_client is not None
        voice = await self._connect_or_validate(ctx)
        if voice is None or ctx.guild is None:
            return
        async with ctx.typing():
            try:
                track = await self.music_service.enqueue(ctx.guild.id, query, ctx.author.id)
            except (ValueError, QueueFullError, MediaResolutionError) as exc:
                if not was_connected and voice.is_connected():
                    with suppress(discord.HTTPException):
                        await voice.disconnect()
                await ctx.reply(f"⚠️ {exc}")
                return
        await ctx.reply(
            f"➕ Ditambahkan: **{track.safe_title}**",
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await self.players.get(ctx.guild.id).start_if_idle(ctx.channel.id)

    @commands.hybrid_command(name="skip", description="Lewati lagu yang sedang diputar.")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def skip(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self.players.get(ctx.guild.id)
        if not await self._can_control(ctx, player, allow_requester=True):
            return
        await ctx.reply("⏭️ Lagu dilewati." if await player.skip() else "⚠️ Tidak ada lagu yang sedang diputar.")

    @commands.hybrid_command(name="queue", description="Tampilkan antrean lagu server ini.")
    @commands.guild_only()
    async def queue(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        tracks = self.music_service.preview(ctx.guild.id, 10)
        if not tracks:
            await ctx.reply("📭 Antrean kosong.")
            return
        description = "\n".join(f"{index}. {track.safe_title}" for index, track in enumerate(tracks, 1))
        embed = discord.Embed(title="🎶 10 lagu berikutnya", description=description, color=discord.Color.blue())
        await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="remove", description="Hapus satu lagu dari antrean berdasarkan posisi.")
    @commands.guild_only()
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def remove(self, ctx: commands.Context, position: int) -> None:
        if ctx.guild is None:
            return
        player = self.players.get(ctx.guild.id)
        if not await self._can_control(ctx, player, allow_requester=False):
            return
        try:
            track = await self.music_service.remove(ctx.guild.id, position)
        except QueuePositionError:
            await ctx.reply("⚠️ Posisi antrean tidak tersedia.")
            return
        await ctx.reply(
            f"🗑️ Dihapus dari antrean: **{track.safe_title}**",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.hybrid_command(name="move", description="Pindahkan lagu ke posisi antrean lain.")
    @commands.guild_only()
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def move(self, ctx: commands.Context, source: int, destination: int) -> None:
        if ctx.guild is None:
            return
        player = self.players.get(ctx.guild.id)
        if not await self._can_control(ctx, player, allow_requester=False):
            return
        try:
            track = await self.music_service.move(ctx.guild.id, source, destination)
        except QueuePositionError:
            await ctx.reply("⚠️ Posisi asal atau tujuan tidak tersedia.")
            return
        await ctx.reply(
            f"↕️ **{track.safe_title}** dipindahkan ke posisi {destination}.",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.hybrid_command(name="shuffle", description="Acak urutan antrean server ini.")
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def shuffle(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self.players.get(ctx.guild.id)
        if not await self._can_control(ctx, player, allow_requester=False):
            return
        count = await self.music_service.shuffle(ctx.guild.id)
        await ctx.reply(f"🔀 Antrean diacak ({count} lagu)." if count else "📭 Antrean kosong.")

    @commands.hybrid_command(name="clear", description="Kosongkan antrean tanpa menghentikan lagu saat ini.")
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def clear(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self.players.get(ctx.guild.id)
        if not await self._can_control(ctx, player, allow_requester=False):
            return
        count = await self.music_service.clear(ctx.guild.id)
        await ctx.reply(f"🧹 Antrean dikosongkan ({count} lagu)." if count else "📭 Antrean sudah kosong.")

    @commands.hybrid_command(name="loop", description="Atur loop: off, track, atau queue.")
    @commands.guild_only()
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def loop(self, ctx: commands.Context, mode: str) -> None:
        if ctx.guild is None:
            return
        player = self.players.get(ctx.guild.id)
        if not await self._can_control(ctx, player, allow_requester=False):
            return
        try:
            selected = LoopMode(mode.casefold())
        except ValueError:
            await ctx.reply("⚠️ Mode loop harus `off`, `track`, atau `queue`.")
            return
        player.set_loop_mode(selected)
        labels = {
            LoopMode.OFF: "dimatikan",
            LoopMode.TRACK: "diaktifkan untuk track saat ini",
            LoopMode.QUEUE: "diaktifkan untuk seluruh antrean",
        }
        await ctx.reply(f"🔁 Loop {labels[selected]}.")

    @commands.hybrid_command(name="setdjrole", description="Pilih role DJ untuk server ini.")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def set_dj_role(self, ctx: commands.Context, role: discord.Role) -> None:
        if ctx.guild is None:
            return
        self.guild_settings.set_dj_role(ctx.guild.id, role.id)
        await ctx.reply("✅ Role DJ diperbarui.", allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="setmusicchannel", description="Batasi command musik ke channel ini.")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def set_music_channel(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        if ctx.guild is None:
            return
        self.guild_settings.set_command_channel(ctx.guild.id, channel.id)
        await ctx.reply("✅ Channel command musik diperbarui.", allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="resetmusicconfig", description="Kembalikan konfigurasi musik ke default aman.")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def reset_music_config(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        self.guild_settings.reset(ctx.guild.id)
        await ctx.reply("✅ Konfigurasi musik dikembalikan ke default.")

    @commands.hybrid_command(name="musicconfig", description="Tampilkan konfigurasi musik server.")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def music_config(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        settings = self.guild_settings.get(ctx.guild.id)
        role_value = str(settings.dj_role_id) if settings.dj_role_id else "default: nama role DJ"
        channel_value = str(settings.command_channel_id) if settings.command_channel_id else "semua channel"
        embed = discord.Embed(title="Konfigurasi musik", color=discord.Color.blue())
        embed.add_field(name="DJ role ID", value=role_value, inline=False)
        embed.add_field(name="Command channel ID", value=channel_value, inline=False)
        await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="pause", description="Jeda lagu yang sedang diputar.")
    @commands.guild_only()
    async def pause(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self.players.get(ctx.guild.id)
        if await self._can_control(ctx, player, allow_requester=True):
            await ctx.reply("⏸️ Musik dijeda." if player.pause() else "⚠️ Tidak ada lagu yang bisa dijeda.")

    @commands.hybrid_command(name="resume", description="Lanjutkan lagu yang sedang dijeda.")
    @commands.guild_only()
    async def resume(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self.players.get(ctx.guild.id)
        if await self._can_control(ctx, player, allow_requester=True):
            await ctx.reply("▶️ Musik dilanjutkan." if player.resume() else "⚠️ Musik tidak sedang dijeda.")

    @commands.hybrid_command(name="stop", description="Hentikan musik dan kosongkan antrean.")
    @commands.guild_only()
    async def stop(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self.players.get(ctx.guild.id)
        if await self._can_control(ctx, player, allow_requester=False):
            await player.stop()
            await ctx.reply("⏹️ Musik dihentikan dan antrean dikosongkan.")

    @commands.hybrid_command(name="leave", description="Keluarkan bot dari voice channel.")
    @commands.guild_only()
    async def leave(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self.players.get(ctx.guild.id)
        if await self._can_control(ctx, player, allow_requester=False):
            await self.players.remove(ctx.guild.id)
            await ctx.reply("👋 Bot keluar dari voice channel.")

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        original = getattr(error, "original", error)
        if isinstance(original, commands.CommandOnCooldown):
            await ctx.reply(f"⏳ Tunggu {original.retry_after:.1f} detik sebelum mencoba lagi.")
            return
        if isinstance(original, commands.MissingRequiredArgument):
            await ctx.reply("⚠️ Masukkan judul lagu atau URL.")
            return
        if isinstance(original, commands.NoPrivateMessage):
            await ctx.reply("⚠️ Command musik hanya tersedia di server.")
            return
        if isinstance(original, commands.MissingPermissions):
            await ctx.reply("⛔ Command konfigurasi memerlukan izin Manage Server.")
            return
        if isinstance(original, commands.CheckFailure):
            await ctx.reply("⚠️ Gunakan command musik di channel yang telah dikonfigurasi.")
            return
        LOGGER.exception("Unhandled music command error", exc_info=original)
        await ctx.reply("❌ Terjadi kesalahan internal. Silakan coba lagi nanti.")
