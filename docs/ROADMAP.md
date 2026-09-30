# Delivery Roadmap

Gunakan ID di bawah sebagai unit kerja. Satu PR idealnya menyelesaikan satu ID dan memperbarui status serta acceptance criteria.

## P0 — Secure Foundation

| ID | Pekerjaan | Status | Acceptance criteria |
|---|---|---|---|
| BOT-001 | Clean architecture dan composition root | Selesai | Dependency mengarah adapter → application → domain |
| BOT-002 | Queue/player per guild | Selesai | Test membuktikan queue dua guild terisolasi |
| BOT-003 | Safe voice callback dan idle lifecycle | Selesai | Callback thread-safe; tidak sleep sambil memegang queue lock |
| BOT-004 | URL policy, timeout, dan non-blocking resolver | Selesai | URL palsu ditolak; resolver berjalan via thread dengan timeout |
| BOT-005 | Authorization, cooldown, dan input limits | Selesai | Same-channel dan DJ/requester policy aktif |
| BOT-006 | Docker dan secret hardening | Selesai | `.env` tidak masuk context; non-root/read-only container |
| BOT-007 | Baseline unit tests | Selesai | Domain, service, config, URL policy diuji |

## P1 — Reliable Music Experience

| ID | Pekerjaan | Dependency | Status | Acceptance criteria |
|---|---|---|---|---|
| BOT-101 | Refresh stream tepat sebelum playback | BOT-004 | Selesai | Track menunggu >1 jam tetap dapat dimainkan |
| BOT-102 | Queue remove/move/clear/shuffle | BOT-002 | Selesai | Operasi atomic per guild dan unit-tested |
| BOT-103 | Loop track/queue | BOT-102 | Selesai | Mode off/track/queue konsisten setelah skip/stop |
| BOT-104 | Now-playing embed dan button controls | BOT-003 | Selesai | Button memakai authorization yang sama dengan command |
| BOT-105 | Config role DJ dan command channel | BOT-005 | Selesai | Setting tersimpan per guild dan mempunyai default aman |
| BOT-106 | Playlist preview dan confirmation | BOT-004 | Belum | Ada batas item dan user harus mengonfirmasi bulk enqueue |
| BOT-107 | Slash-command-first migration | BOT-104 | Belum | Prefix opsional; Message Content Intent dapat dimatikan |
| BOT-108 | Voice reconnect policy | BOT-003 | Belum | Backoff terbatas, tidak reconnect loop tanpa batas |

## P2 — Persistence and Operations

| ID | Pekerjaan | Dependency | Status | Acceptance criteria |
|---|---|---|---|---|
| BOT-201 | Repository port untuk guild settings | BOT-105 | Belum | Application tidak tergantung SQLite/Redis |
| BOT-202 | SQLite adapter dan migration | BOT-201 | Belum | Migration idempotent dan backup terdokumentasi |
| BOT-203 | Persistent queue metadata | BOT-101, BOT-202 | Belum | Tidak menyimpan direct stream URL; restore opt-in per guild |
| BOT-204 | Metrics dan health endpoint | BOT-001 | Belum | Tidak mengekspos query, title, token, atau user content |
| BOT-205 | Structured logging dan correlation ID | BOT-204 | Belum | Guild/user ID di-hash atau diminimalkan sesuai kebutuhan |
| BOT-206 | CI quality/security pipeline | BOT-007 | Sebagian; workflow siap, belum dieksekusi di CI | compile, test, lint, dependency scan, dan image build otomatis |

## P3 — Product Expansion

- BOT-301: configurable welcome templates.
- BOT-302: dashboard operator dan guild settings.
- BOT-303: localization Indonesia/English.
- BOT-304: lyrics melalui provider legal/berlisensi.
- BOT-305: aggregate usage analytics dengan privacy review.

## Urutan Eksekusi Berikutnya

1. BOT-101 agar queue panjang stabil.
2. BOT-102 dan BOT-103 untuk kontrol queue lengkap.
3. BOT-104 lalu BOT-107 untuk UI Discord modern dan mengurangi privileged intent.
4. BOT-105 sebelum persistence.
5. BOT-201 → BOT-202 → BOT-203 sebagai satu rangkaian data architecture.
6. BOT-206 sebelum deployment publik.
