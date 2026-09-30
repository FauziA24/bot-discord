# Security and Privacy

## 1. Data yang Diproses

- Discord user ID untuk mencatat requester selama track berada di memory.
- Guild ID dan channel ID untuk isolasi queue dan notifikasi.
- Query lagu dan metadata hasil provider selama runtime.
- Token Discord dan kredensial Spotify dari environment.

Bot tidak merekam voice, tidak menerima audio user, dan tidak menyimpan isi pesan atau riwayat lagu secara permanen.

## 2. Trust Boundaries

1. Input pengguna Discord dianggap tidak tepercaya.
2. Metadata YouTube/Spotify dianggap tidak tepercaya.
3. Stream URL hanya berasal dari resolver yang dikontrol aplikasi.
4. `.env`, CI secret, container registry, dan log adalah boundary operator.

## 3. Threat Model

| Ancaman | Kontrol saat ini | Pekerjaan lanjutan |
|---|---|---|
| Cross-guild queue/control | State dan player per guild | Integration test dua guild |
| Command abuse/DoS | cooldown, queue/query limit, timeout, global concurrency semaphore | deployment-level rate monitoring |
| Arbitrary URL/SSRF | allowlist host dan scheme | DNS/IP egress policy pada deployment |
| Token leakage | `.gitignore`, `.dockerignore`, pesan error aman | secret manager dan rotation runbook |
| Mention injection | `AllowedMentions.none`, judul dipotong | sanitasi embed terpusat |
| Blocking event loop | `asyncio.to_thread`, timeout | metrics event-loop lag |
| Unauthorized voice control | same-channel + requester/DJ/permissions | configurable policy per guild |
| Dependency compromise | exact version pins, minimal packages | lockfile/hash dan dependency scanning |
| Container breakout | non-root, cap drop, read-only, no-new-privileges | image scan dan digest pin |

## 4. Aturan Wajib

- Jangan pernah membaca atau mencetak isi `.env` dalam test, log, prompt AI, atau output command.
- Jangan menambahkan `discord.ext.voice_recv`, sink, recording, atau transcription tanpa PRD dan consent flow baru.
- Jangan mengaktifkan `nocheckcertificate` atau menonaktifkan TLS verification.
- Jangan meneruskan exception vendor mentah kepada pengguna.
- Jangan menerima URL baru hanya dengan substring/regex longgar; parse scheme dan hostname.
- Jangan menjalankan shell dari query pengguna.
- Jangan menaruh user-generated text dalam mention-enabled response.

## 5. Incident Response Ringkas

Jika token diduga bocor:

1. Reset token di Discord Developer Portal segera.
2. Cabut/rotasi Spotify secret bila relevan.
3. Hentikan deployment lama dan hapus image/cache yang mungkin menyimpan secret.
4. Audit Git history, registry, CI logs, dan host logs.
5. Deploy ulang dengan secret baru.
6. Dokumentasikan akar masalah dan tambahkan regression control.

## 6. Security Acceptance Gate

- Unit test allowlist URL lulus.
- `.env` diabaikan Git dan Docker.
- Tidak ada global queue/player.
- Command kontrol memiliki authorization check.
- Dependency baru memiliki alasan, versi pin, dan review lisensi/keamanan.
- Perubahan voice tidak menambah kemampuan receive/record tanpa persetujuan eksplisit.
