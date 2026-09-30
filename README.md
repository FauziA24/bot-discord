# Discord Music Bot

Bot musik Discord berbasis Python 3.12 dengan antrean terisolasi per server, YouTube search, Spotify track lookup, voice authorization, dan clean architecture yang dapat diuji.

## Fitur Saat Ini

- Search YouTube atau URL YouTube.
- URL track Spotify opsional; metadata diterjemahkan menjadi pencarian YouTube.
- Queue FIFO terpisah untuk setiap guild.
- Stream URL di-refresh tepat sebelum playback agar antrean panjang tetap dapat diputar.
- `play`, `queue`, `remove`, `move`, `shuffle`, `clear`, `loop`, `skip`, `pause`, `resume`, `stop`, dan `leave`.
- Prefix command dan hybrid/slash command dari handler yang sama.
- Same-channel enforcement, requester/DJ/admin authorization, cooldown, dan input limit.
- Role DJ dan channel command dapat dikonfigurasi per guild oleh pengguna dengan Manage Server.
- Auto-disconnect ketika idle.
- Now-playing embed dengan progress durasi dan tombol Pause, Resume, Skip, serta Stop.
- Welcome message tanpa mengaktifkan mention yang tidak diperlukan.
- Docker non-root dengan filesystem read-only dan build context tanpa secret.

Bot hanya mengirim audio ke voice channel. Bot tidak merekam atau mentranskripsikan suara pengguna.

## Dokumentasi Pengembangan

Mulai dari [docs/README.md](docs/README.md). Dokumen utama:

- [PRD](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Security](docs/SECURITY.md)
- [Roadmap](docs/ROADMAP.md)
- [AI Execution Guide](docs/AI_EXECUTION_GUIDE.md)

## Struktur

```text
src/discord_music_bot/
├── domain/          # Entitas dan aturan queue murni
├── application/     # Use case dan integration ports
├── adapters/
│   ├── discord/     # Commands, permissions, player lifecycle
│   └── media/       # yt-dlp dan Spotify
├── config.py        # Validasi environment
└── main.py          # Composition root
```

## Setup Lokal

1. Buat virtual environment dan install dependency:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Install FFmpeg dan pastikan `ffmpeg` tersedia di `PATH`.

3. Siapkan environment:

```powershell
Copy-Item .env.example .env
```

Isi `DISCORD_TOKEN`. Spotify membutuhkan `SPOTIPY_CLIENT_ID` dan `SPOTIPY_CLIENT_SECRET` secara bersamaan.

4. Jalankan:

```powershell
python index.py
```

Untuk mendaftarkan slash commands, jalankan satu kali dengan `SYNC_COMMANDS=true`, tunggu sinkronisasi, lalu kembalikan ke `false` agar startup tidak selalu melakukan global sync.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose logs -f discord_bot
```

File `.env` tidak masuk Git atau Docker image. Untuk production, gunakan secret manager platform deployment.

## Commands dan Hak Akses

| Command | Pengguna |
|---|---|
| `play`, `queue` | Member di voice channel yang sesuai |
| `skip`, `pause`, `resume` | Requester lagu, role `DJ`, Manage Server, atau Move Members |
| `remove`, `move`, `shuffle`, `clear` | Role `DJ`, Manage Server, atau Move Members |
| `loop off\|track\|queue` | Role `DJ`, Manage Server, atau Move Members |
| `stop`, `leave` | Role `DJ`, Manage Server, atau Move Members |
| `setdjrole`, `setmusicchannel`, `resetmusicconfig`, `musicconfig` | Manage Server |

Contoh prefix:

```text
!play bohemian rhapsody
!play https://youtu.be/...
!play https://open.spotify.com/track/...
!queue
!move 3 1
!remove 2
!shuffle
!clear
!loop queue
!skip
```

## Test

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m compileall -q index.py src tests
python -m unittest discover -s tests -v
python -m pip check
```

Unit test tidak memerlukan token Discord atau koneksi internet.

CI menjalankan compile, unit test, Ruff, Bandit, pip-audit, policy security internal, validasi Compose, build image, serta pemeriksaan runtime non-root dan FFmpeg. Lihat [AI Release Runbook](docs/AI_RELEASE_RUNBOOK.md) untuk gate staging sampai production; deployment eksternal selalu memerlukan approval operator dan secret manager.

## Discord Developer Portal

Prefix commands memerlukan Message Content Intent. Welcome message memerlukan Server Members Intent. Jika BOT-107 pada roadmap selesai dan prefix dimatikan, Message Content Intent dapat dihapus.

Permission bot minimum:

- View Channels
- Send Messages
- Embed Links
- Connect
- Speak

Jangan memberikan Administrator jika permission di atas sudah cukup.
