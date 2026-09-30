from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

import yt_dlp
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

from discord_music_bot.application import MediaResolutionError
from discord_music_bot.domain import Track

LOGGER = logging.getLogger(__name__)

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "default_search": "ytsearch",
    "quiet": True,
    "no_warnings": True,
    "socket_timeout": 15,
    "extract_flat": False,
}


def _is_youtube_url(value: str) -> bool:
    try:
        parsed = urlparse(value if "://" in value else f"https://{value}")
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and host in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }


def _is_spotify_track_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").lower() == "open.spotify.com"
        and len(parts) == 2
        and parts[0] == "track"
    )


class YtDlpTrackResolver:
    def __init__(self, spotify_client_id: str | None, spotify_client_secret: str | None) -> None:
        self._spotify: Spotify | None = None
        self._resolution_slots = asyncio.Semaphore(4)
        if spotify_client_id and spotify_client_secret:
            credentials = SpotifyClientCredentials(
                client_id=spotify_client_id,
                client_secret=spotify_client_secret,
            )
            self._spotify = Spotify(client_credentials_manager=credentials, requests_timeout=10)

    async def resolve(self, query: str, requested_by: int) -> Track:
        return await self._resolve_query(query, query, requested_by)

    async def refresh(self, track: Track) -> Track:
        # Provider stream URLs are short-lived. Prefer the canonical YouTube page,
        # but run it through the same allowlist as all other untrusted input.
        refresh_query = track.webpage_url or track.original_query
        return await self._resolve_query(refresh_query, track.original_query, track.requested_by)

    async def _resolve_query(self, query: str, original_query: str, requested_by: int) -> Track:
        try:
            async with self._resolution_slots:
                normalized_query = await self._normalize_query(query)
                return await asyncio.wait_for(
                    asyncio.to_thread(self._extract, normalized_query, original_query, requested_by),
                    timeout=30,
                )
        except MediaResolutionError:
            raise
        except TimeoutError as exc:
            raise MediaResolutionError("Pencarian lagu melewati batas waktu.") from exc
        except Exception as exc:
            LOGGER.exception("Media resolution failed")
            raise MediaResolutionError("Lagu tidak dapat ditemukan atau diputar.") from exc

    async def _normalize_query(self, query: str) -> str:
        if _is_spotify_track_url(query):
            if self._spotify is None:
                raise MediaResolutionError("Integrasi Spotify belum dikonfigurasi.")
            data = await asyncio.to_thread(self._spotify.track, query)
            artists = data.get("artists") or []
            artist = artists[0].get("name", "") if artists else ""
            return f"ytsearch1:{data.get('name', '')} {artist}".strip()
        if _is_youtube_url(query):
            return query
        if "://" in query:
            raise MediaResolutionError("Hanya URL YouTube atau track Spotify yang diperbolehkan.")
        return f"ytsearch1:{query}"

    @staticmethod
    def _extract(search_query: str, original_query: str, requested_by: int) -> Track:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(search_query, download=False)
        if not info:
            raise MediaResolutionError("Media tidak ditemukan.")
        video = info.get("entries", [None])[0] if "entries" in info else info
        if not video or not video.get("url"):
            raise MediaResolutionError("Media tidak memiliki stream audio yang dapat diputar.")
        return Track(
            title=str(video.get("title") or "Unknown title"),
            stream_url=str(video["url"]),
            requested_by=requested_by,
            original_query=original_query,
            webpage_url=video.get("webpage_url") or video.get("original_url"),
            duration_seconds=video.get("duration"),
        )
