# Product Requirements Document — Discord Music Bot

Status: baseline v0.2  
Owner: project maintainer  
Last updated: 2026-09-30

## 1. Ringkasan

Bot menyediakan pemutaran musik yang aman dan stabil untuk Discord melalui pencarian YouTube dan URL track Spotify. Produk harus dapat digunakan oleh banyak server tanpa kebocoran antrean atau kontrol antar-server, serta mudah dikembangkan melalui modul yang dapat diuji.

## 2. Masalah yang Diselesaikan

- Pengguna ingin meminta dan mengontrol musik tanpa meninggalkan Discord.
- Administrator memerlukan batasan agar command tidak mudah disalahgunakan.
- Satu instance bot harus melayani banyak guild dengan state yang terisolasi.
- Developer dan AI memerlukan spesifikasi serta kontrak arsitektur yang tidak ambigu.

## 3. Sasaran

1. Pemutaran audio stabil dengan antrean FIFO per guild.
2. Privasi voice: bot hanya mengirim audio dan tidak merekam pengguna.
3. Kontrol command berbasis channel, requester, role DJ, dan izin Discord.
4. Waktu respons command non-media di bawah 1 detik pada kondisi normal.
5. Perubahan domain/application dapat diuji tanpa koneksi Discord.
6. Deployment dapat direproduksi melalui Docker tanpa menyimpan token dalam image.

## 4. Bukan Sasaran Saat Ini

- Merekam, mentranskripsi, atau menyimpan suara pengguna.
- Mengunduh dan menyimpan file musik secara permanen.
- Mengakali DRM, paywall, region lock, atau pembatasan sumber media.
- Menyediakan layanan streaming publik di luar voice channel Discord.
- Dashboard administrasi web pada release v0.2.

## 5. Pengguna

- **Listener:** mencari lagu, melihat antrean, dan meminta lagu.
- **Requester:** dapat melewati atau menjeda lagu yang dia minta ketika berada di channel yang sama.
- **DJ:** mengontrol playback dan antrean melalui role bernama `DJ`.
- **Administrator:** memiliki kontrol penuh melalui izin Manage Server atau Move Members.
- **Operator:** menjalankan bot, mengelola secret, log, dan deployment.

## 6. Kebutuhan Fungsional

| ID | Kebutuhan | Prioritas | Status |
|---|---|---:|---|
| FR-001 | `play` menerima kata pencarian, URL YouTube, atau URL track Spotify | P0 | Selesai |
| FR-002 | Antrean dan current track terisolasi per guild | P0 | Selesai |
| FR-003 | `skip`, `pause`, `resume`, `stop`, dan `leave` memvalidasi voice channel | P0 | Selesai |
| FR-004 | Kontrol sensitif memakai requester/role DJ/izin Discord | P0 | Selesai |
| FR-005 | Bot menolak URL selain sumber yang diizinkan | P0 | Selesai |
| FR-006 | Queue mempunyai kapasitas dan query mempunyai batas panjang | P0 | Selesai |
| FR-007 | Bot keluar otomatis ketika idle | P0 | Selesai |
| FR-008 | Prefix commands dan slash commands tersedia dari handler yang sama | P1 | Sebagian; sync opsional |
| FR-009 | Playlist YouTube dan Spotify diproses dengan preview serta konfirmasi | P1 | Belum |
| FR-010 | Loop, shuffle, remove, move, dan clear queue | P1 | Selesai |
| FR-011 | Now-playing embed mempunyai progress dan tombol kontrol | P1 | Selesai |
| FR-012 | Konfigurasi role DJ dan channel command per guild | P1 | Selesai; persistence lintas restart di P2 |
| FR-013 | Queue dapat dipulihkan setelah restart | P2 | Belum |
| FR-014 | Welcome message dapat dikonfigurasi per guild | P2 | Belum |
| FR-015 | Dashboard operator menampilkan health tanpa data pesan/suara | P3 | Belum |

## 7. Kebutuhan Non-Fungsional

| ID | Kebutuhan |
|---|---|
| NFR-001 | Tidak ada operasi jaringan/blocking berat di event loop Discord. |
| NFR-002 | Callback audio lintas thread harus memakai API thread-safe. |
| NFR-003 | Token tidak boleh masuk Git, log, Docker build context, atau exception pengguna. |
| NFR-004 | Setiap guild memiliki queue, lock, player, dan lifecycle independen. |
| NFR-005 | Error eksternal dicatat secara internal dan diterjemahkan menjadi pesan aman. |
| NFR-006 | Domain/application mempunyai unit test tanpa Discord/network. |
| NFR-007 | Dependency production dipin untuk build reproducible. |
| NFR-008 | Container berjalan sebagai non-root dengan capability minimum. |

## 8. Acceptance Criteria Release v0.2

- Dua guild dapat menambah dan memutar queue tanpa state tercampur.
- Pengguna di channel lain tidak dapat mengontrol player.
- Pengguna tanpa role/izin tidak dapat menjalankan `stop` atau `leave`.
- URL dengan domain tiruan seperti `youtube.com.evil.example` ditolak.
- Missing token atau FFmpeg menghasilkan startup error yang jelas.
- `python -m unittest discover -s tests -v` lulus.
- `python -m compileall -q index.py src tests` lulus.
- Docker build context mengecualikan `.env`, virtualenv, Git, docs, dan test.
- Tidak ada fitur voice receive/recording dalam dependency atau kode runtime.

## 9. Metrik Operasional

- Persentase command berhasil, dikelompokkan per command tanpa menyimpan argumen pengguna.
- Jumlah media resolution timeout/error.
- Jumlah voice reconnect dan unexpected disconnect.
- Panjang queue per guild sebagai agregat, tanpa identitas atau judul lagu pada telemetry.
- Waktu resolusi media p50/p95.

## 10. Risiko Produk

- Perubahan YouTube dapat merusak ekstraksi yt-dlp; mitigasi melalui update terjadwal dan smoke test.
- Stream URL dapat kedaluwarsa pada queue panjang; BOT-101 memitigasinya dengan refresh tepat sebelum playback.
- Slash command global dapat membutuhkan waktu propagasi; gunakan guild sync saat development.
- Hak cipta dan ToS sumber media harus ditinjau oleh operator sebelum publikasi luas.
