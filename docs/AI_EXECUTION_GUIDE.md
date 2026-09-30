# AI Execution Guide

Dokumen ini adalah kontrak kerja untuk AI atau developer yang melanjutkan proyek.

## 1. Source of Truth

Urutan prioritas saat terjadi konflik:

1. Keamanan dan privacy rules di `SECURITY.md`.
2. Acceptance criteria di `PRD.md`.
3. Dependency rule di `ARCHITECTURE.md` dan ADR.
4. Task/status di `ROADMAP.md`.
5. Implementasi dan test saat ini.

Jangan mengubah perilaku produk secara material tanpa memperbarui PRD dan roadmap.

## 2. Workflow Wajib

1. Baca seluruh `changelog.md` untuk memahami perubahan, keterbatasan, dan pekerjaan terakhir.
2. Pilih satu ID roadmap yang belum selesai.
3. Baca PRD, architecture, security, dan file terkait.
4. Tulis rencana perubahan singkat dan identifikasi threat/data impact.
5. Implementasikan logic domain/application sebelum adapter bila memungkinkan.
6. Tambahkan atau ubah test untuk acceptance criteria.
7. Jalankan quality gates.
8. Perbarui `changelog.md`, status roadmap, dan dokumentasi perilaku.
9. Laporkan file berubah, hasil test, keterbatasan, dan pekerjaan lanjutan.

## 3. Boundary Rules

- `domain/`: standard library saja; tidak boleh mengetahui Discord/provider.
- `application/`: boleh mengimpor domain; integrasi didefinisikan sebagai Protocol/port.
- `adapters/`: mengimplementasikan port dan menangani vendor-specific errors.
- `main.py`: composition root; tidak menyimpan business logic.
- Satu guild tidak boleh membaca/mengubah state guild lain.
- Semua network blocking SDK dipanggil melalui `asyncio.to_thread` atau client async.
- Semua background task harus punya lifecycle cancellation/cleanup.

## 4. Quality Gates

Jalankan dari root proyek:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m compileall -q index.py src tests
python -m unittest discover -s tests -v
python -m pip check
```

Jika Docker tersedia:

```powershell
docker compose config
docker build -t discord-music-bot:local .
```

Jika Ruff tersedia:

```powershell
ruff check .
```

Perubahan tidak dianggap selesai jika test relevan gagal atau belum ditambahkan.

## 5. Task Prompt Template untuk AI

```text
Kerjakan ROADMAP task <BOT-ID> saja.
Baca docs/PRD.md, docs/ARCHITECTURE.md, docs/SECURITY.md,
docs/ROADMAP.md, dan docs/AI_EXECUTION_GUIDE.md.

Tujuan:
<salin tujuan dan acceptance criteria>

Batasan:
- Pertahankan dependency rule clean architecture.
- Jangan membaca/menampilkan .env atau secret.
- Jangan menambah voice recording/receive.
- Tambahkan test dan jalankan semua quality gates yang tersedia.
- Perbarui status roadmap hanya jika acceptance criteria benar-benar terpenuhi.

Hasil akhir harus menyebutkan perubahan, verifikasi, risiko tersisa,
dan rekomendasi task berikutnya.
```

## 6. Definition of Done

- Acceptance criteria task terpenuhi dan dapat ditunjukkan lewat test atau evidence.
- Tidak ada secret, user content, atau direct stream URL baru yang dipersist.
- Error path dan concurrency path dipertimbangkan.
- Dokumentasi dan contoh command sesuai kode.
- Test deterministic dan tidak memerlukan Discord/YouTube untuk unit layer.
- Tidak ada unrelated refactor dalam task yang sama.

## 7. Known Constraints

- Integration test Discord voice belum tersedia.
- Docker tidak selalu tersedia di workstation developer.
- yt-dlp mengikuti perubahan upstream provider dan perlu update terkontrol.
- Metadata awal diselesaikan saat enqueue; stream URL selalu di-refresh lagi tepat sebelum playback (BOT-101).
- Role DJ saat ini hardcoded berdasarkan nama; BOT-105 akan membuatnya configurable.
