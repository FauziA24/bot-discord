# Changelog

Dokumen ini mencatat perubahan implementasi yang telah selesai dan konteks yang perlu diketahui sebelum pekerjaan berikutnya.

> **Aturan kerja:** baca seluruh `changelog.md` sebelum mengeksekusi step atau fitur berikutnya. Tambahkan entri baru setelah implementasi dan verifikasinya selesai.

## 2026-09-30 — BOT-101: Refresh stream sebelum playback

Status: selesai.

### Perubahan

- Menambahkan kontrak `TrackResolver.refresh(track)` pada application port.
- Menambahkan `MusicService.next_for_playback(guild_id)` yang mengambil item queue lalu meminta URL stream baru.
- Mengubah `GuildPlayer` agar hanya memberikan URL hasil refresh terbaru kepada FFmpeg.
- Track yang gagal di-refresh dilewati dengan pesan pengguna yang aman, kemudian player melanjutkan ke track berikutnya.
- Resolver tetap memakai allowlist URL, concurrency semaphore, timeout, dan `asyncio.to_thread` agar pekerjaan blocking tidak masuk event loop.
- Memperbarui PRD, architecture, roadmap, AI execution guide, dan README agar sesuai dengan perilaku baru.

### Test dan verifikasi

- `python -m compileall -q index.py src tests`: lulus.
- `python -m unittest discover -s tests -v`: 15 test lulus.
- `python -m pip check` pada `bot_env`: lulus, tidak ada dependency rusak.
- `git diff --check`: lulus.
- Unit test baru membuktikan URL lama diganti sebelum playback dan track yang gagal di-refresh dilewati.

### Keterbatasan lingkungan

- Ruff tidak tersedia di environment proyek.
- Docker tidak tersedia sehingga `docker compose config` dan image build belum dijalankan.
- `pip check` pada Python global memiliki konflik paket workstation yang tidak terkait proyek; environment proyek `bot_env` bersih.

### Pekerjaan berikutnya

- BOT-102 telah diselesaikan pada entri berikutnya.

## 2026-09-30 — BOT-102: Operasi mutasi queue

Status: selesai.

### Perubahan

- Menambahkan operasi domain `remove`, `move`, `shuffle`, dan `clear` pada `GuildQueue`.
- Menambahkan validasi posisi queue melalui `QueuePositionError`; antarmuka application dan command memakai posisi mulai dari 1.
- Semua mutasi dibungkus lock milik guild pada `MusicService` sehingga perubahan atomic dan tidak menyentuh queue guild lain.
- Menambahkan hybrid command `remove`, `move`, `shuffle`, dan `clear`.
- Command mutasi queue memakai validasi same-channel dan hanya dapat dijalankan role DJ atau pengguna dengan Manage Server/Move Members.
- `clear` hanya mengosongkan antrean dan tidak menghentikan track yang sedang diputar; `stop` tetap melakukan keduanya.

### Test dan verifikasi

- Compile Python: lulus.
- Seluruh 22 unit test: lulus.
- Test baru mencakup remove/move, posisi invalid tanpa mutasi parsial, shuffle deterministik, jumlah hasil clear, posisi 1-based, serta isolasi antar-guild.

### Dampak keamanan dan data

- Tidak ada data baru yang disimpan.
- Tidak ada dependency atau kemampuan voice receive/recording baru.
- Judul track dalam respons tetap disanitasi melalui `safe_title` dan mention dinonaktifkan.

### Pekerjaan berikutnya

- BOT-103 telah diselesaikan pada entri berikutnya.

## 2026-09-30 — BOT-103: Loop track dan queue

Status: selesai.

### Perubahan

- Menambahkan `LoopMode` dengan mode `off`, `track`, dan `queue`.
- Mode loop disimpan pada `GuildPlayer`, sehingga state tetap terisolasi per guild.
- Loop track me-refresh URL stream sebelum setiap pengulangan.
- Loop queue memasukkan track yang selesai ke ujung queue di bawah lock guild.
- Skip tidak mengulang track yang dilewati; stop dan leave mereset loop ke `off`.
- Menambahkan hybrid command `loop off|track|queue` dengan same-channel dan otorisasi DJ/admin.

### Test dan verifikasi

- Compile Python: lulus.
- Seluruh 27 unit test: lulus.
- Test baru mencakup refresh loop track, rotasi loop queue, manual skip tanpa repeat, reset setelah stop, dan isolasi requeue antar-guild.

### Dampak keamanan dan data

- State loop hanya berada di memori dan dibatasi per guild.
- Tidak ada dependency, persistence, atau kemampuan voice receive baru.

### Pekerjaan berikutnya

- BOT-104 telah diselesaikan pada entri berikutnya.

## 2026-09-30 — BOT-104: Now-playing embed dan button controls

Status: selesai.

### Perubahan

- Mengganti notifikasi teks playback dengan embed now-playing yang menampilkan judul aman, progress bar, waktu berjalan, dan durasi.
- Menambahkan tombol Pause, Resume, Skip, dan Stop dengan respons ephemeral.
- Mengekstrak pemeriksaan same-channel dan permission ke policy bersama yang dipakai command serta tombol.
- Requester dapat memakai Pause/Resume/Skip; Stop tetap hanya untuk DJ atau Manage Server/Move Members.
- View tombol lama dihentikan ketika track berganti, stop, atau leave untuk menjaga lifecycle background Discord UI.

### Test dan verifikasi

- Compile Python: lulus.
- Seluruh 29 unit test: lulus.
- Test baru memeriksa format durasi, sanitasi judul, dan field progress embed.

### Dampak keamanan dan data

- Metadata provider tetap dianggap tidak tepercaya dan judul melewati `safe_title`.
- Respons button bersifat ephemeral dan tidak mengaktifkan mention.
- Tidak ada data baru yang dipersist atau kemampuan voice receive baru.

### Pekerjaan berikutnya

- BOT-105 telah diselesaikan pada entri berikutnya.

## 2026-09-30 — BOT-105: Konfigurasi role DJ dan command channel

Status: selesai.

### Perubahan

- Menambahkan `GuildSettingsService` dan model immutable `GuildSettings` dengan state terisolasi per guild.
- Default aman tetap memakai role bernama `DJ` dan mengizinkan command di semua channel.
- Administrator dapat memilih role berdasarkan ID melalui `setdjrole` dan membatasi command melalui `setmusicchannel`.
- Menambahkan `musicconfig` dan `resetmusicconfig`; command konfigurasi memerlukan Manage Server dan dikecualikan dari pembatasan channel untuk recovery.
- Command dan button controls membaca role DJ terkonfigurasi dari service yang sama.
- Settings dihapus ketika bot dikeluarkan dari guild.

### Test dan verifikasi

- Compile Python: lulus.
- Seluruh 32 unit test: lulus.
- Test baru membuktikan default aman, isolasi settings antar-guild, dan reset yang hanya memengaruhi guild target.

### Dampak keamanan dan data

- Hanya Discord role ID dan channel ID yang disimpan sementara di memori.
- Persistence lintas restart belum ditambahkan; repository port dan SQLite tetap menjadi scope BOT-201/BOT-202.
- Tidak ada dependency atau kemampuan voice receive baru.

### Pekerjaan berikutnya

- BOT-206 dimulai lebih awal sebagai security/release gate dan dicatat pada entri berikutnya. BOT-106 tetap belum selesai.

## 2026-09-30 — BOT-206 (sebagian): Secure CI dan release gates

Status: sebagian; implementasi workflow selesai, tetapi eksekusi GitHub CI dan Docker belum memiliki evidence.

### Perubahan

- Menambahkan workflow least-privilege untuk compile, unit test, Ruff, Bandit, pip-audit, policy gate, Compose validation, Docker build, non-root runtime, dan FFmpeg check.
- Checkout CI tidak menyimpan credential dan job mempunyai timeout serta concurrency cancellation.
- Menambahkan Dependabot mingguan untuk Python, GitHub Actions, dan Docker.
- Menambahkan `scripts/security_gate.py` untuk exact dependency pin, forbidden insecure patterns, Docker ignore policy, dan tracked `.env` detection.
- Menambahkan `docs/AI_RELEASE_RUNBOOK.md` dengan gate fail-closed dari feature complete sampai monitoring/maintenance serta stop conditions untuk secret dan approval manusia.
- Menambahkan tooling development terpin: Ruff 0.16.9, Bandit 1.9.4, dan pip-audit 2.10.1.

### Temuan dan remediasi security

- pip-audit awal menemukan dua vulnerability pada PyNaCl 1.5.0.
- Runtime kini mem-pin PyNaCl 1.6.2 secara eksplisit dan memakai `discord.py==2.7.1` tanpa extra voice lama yang mengunci dependency rentan.
- Audit ulang: tidak ada vulnerability dependency yang diketahui.

### Verifikasi lokal

- Compile dan 32 unit test: lulus.
- Ruff: lulus.
- Bandit severity medium/high: lulus.
- Internal security policy gate: lulus.
- `pip check`: lulus.
- pip-audit: tidak menemukan vulnerability yang diketahui.
- Docker belum tersedia; build dan runtime verification menunggu GitHub CI atau host Docker.

### Pekerjaan berikutnya

- Push/commit harus menjalankan workflow baru; BOT-206 hanya boleh menjadi Selesai setelah kedua job CI hijau.
- Feature completion tetap melanjutkan BOT-106, BOT-107, dan BOT-108 sebelum staging.
- Observability BOT-204/BOT-205 wajib selesai sebelum closed beta.
