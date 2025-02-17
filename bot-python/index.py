import os
import discord
import asyncio
import yt_dlp as youtube_dl
import shutil
import re
from discord.ext import commands
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

sp = None
if SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET:
    sp = Spotify(client_credentials_manager=SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)

FFMPEG_PATH = shutil.which("ffmpeg")
if not FFMPEG_PATH:
    print("⚠️ FFMPEG tidak ditemukan! Mohon install dengan `apt install ffmpeg`.")

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'ytsearch',
    'quiet': True,
    'extract_flat': False,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'postprocessors': [{'key': 'FFmpegFixupM4a'}]
}

class MusicManager:
    def __init__(self):
        self.music_queue = []
        self.current_song = None
        self.playing_lock = asyncio.Lock()
    
    async def play_next(self, ctx):
        voice_client = ctx.voice_client
        async with self.playing_lock:
            if not self.music_queue:
                self.current_song = None
                await asyncio.sleep(5)
                if voice_client and voice_client.is_connected():
                    await voice_client.disconnect()
                return
            
            song = self.music_queue.pop(0)
            self.current_song = song
            source = discord.FFmpegPCMAudio(song['url'], executable=FFMPEG_PATH, **FFMPEG_OPTIONS)
            voice_client.play(source, after=lambda e: bot.loop.create_task(self.play_next(ctx)))
            await ctx.send(f"🎶 Now playing: **{song['title']}**")

    async def fetch_spotify_track(self, url):
        if not sp:
            return None
        track_info = sp.track(url)
        return f"ytsearch:{track_info['name']} {track_info['artists'][0]['name']}"
    
    async def play_command(self, ctx, query):
        if not query:
            return await ctx.reply("⚠ Mohon masukkan judul lagu atau link.")
        
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("⚠ Anda harus berada di saluran suara terlebih dahulu.")
        
        voice_channel = ctx.author.voice.channel
        voice_client = ctx.voice_client
        if not voice_client:
            voice_client = await voice_channel.connect()
        
        if "open.spotify.com/track" in query:
            query = await self.fetch_spotify_track(query)
            if not query:
                return await ctx.reply("⚠ Tidak dapat mengambil lagu dari Spotify.")
        
        search_query = query if re.match(r"^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.*$", query) else f"ytsearch:{query}"
        
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
                video = info['entries'][0] if 'entries' in info else info
            except Exception as e:
                return await ctx.reply(f"❌ Gagal mengambil lagu: {e}")
        
        url, title = video.get('url'), video.get('title', 'Unknown Title')
        self.music_queue.append({'title': title, 'url': url})
        await ctx.send(f"🎶 Menambahkan ke antrian: **{title}**")
        
        if not voice_client.is_playing():
            await self.play_next(ctx)
    
    async def skip(self, ctx):
        voice_client = ctx.voice_client
        if not voice_client or not voice_client.is_playing():
            return await ctx.reply("⚠ Tidak ada musik yang sedang diputar.")
        voice_client.stop()
        await ctx.reply("⏭️ Melonjak ke lagu berikutnya...")
    
    async def queue(self, ctx):
        if not self.music_queue:
            return await ctx.reply("⚠ Antrian kosong.")
        queue_list = "\n".join([f"{i+1}. {track['title']}" for i, track in enumerate(self.music_queue[:10])])
        embed = discord.Embed(title="🎵 Antrian (Lagu berikutnya 10)", description=queue_list, color=discord.Color.blue())
        await ctx.reply(embed=embed)
    
    async def stop(self, ctx):
        voice_client = ctx.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            self.music_queue.clear()
            await ctx.reply("⏹️ Musik dihentikan dan antrian dikosongkan.")
    
    async def leave(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_connected():
            await ctx.voice_client.disconnect()
            await ctx.reply("👋 Bot telah keluar dari saluran suara.")

bot.music_manager = MusicManager()

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="general")
    if channel:
        await channel.send(f"👋 Selamat datang, {member.mention}! Nikmati server ini.")

@bot.command(name="play")
async def play(ctx, *, query=None):
    await bot.music_manager.play_command(ctx, query)

@bot.command(name="skip")
async def skip(ctx):
    await bot.music_manager.skip(ctx)

@bot.command(name="queue")
async def queue(ctx):
    await bot.music_manager.queue(ctx)

@bot.command(name="stop")
async def stop(ctx):
    await bot.music_manager.stop(ctx)

@bot.command(name="leave")
async def leave(ctx):
    await bot.music_manager.leave(ctx)

bot.run(TOKEN)
