# AI Release Runbook — Fail-Closed Production Delivery

Dokumen ini mengatur AI/developer yang membawa aplikasi dari feature development sampai maintenance. AI wajib membaca `changelog.md`, `SECURITY.md`, PRD, architecture, roadmap, dan dokumen ini sebelum memulai satu tahap.

## Prinsip wajib

- Jangan pernah membaca, mencetak, menyalin, atau memasukkan secret ke prompt, log, artifact, image, atau pull request.
- Jangan menggunakan token production untuk test, staging, pull request, atau build.
- Jangan melewati gate gagal, menurunkan severity, mematikan TLS, atau menambahkan exception audit tanpa review manusia terdokumentasi.
- Deployment staging/production memerlukan environment terpisah, secret manager, approval manusia, dan artifact immutable yang sama.
- AI tidak boleh menandai staging, beta, RC, production, atau monitoring selesai hanya berdasarkan konfigurasi; harus ada evidence eksekusi bertanggal.
- Rollback harus tersedia sebelum rollout. Production memakai canary/bertahap, bukan penggantian serentak.

## Gates

1. **Feature complete:** seluruh scope release pada PRD/roadmap selesai, acceptance test lulus, dan tidak ada status “Sebagian/Belum”.
2. **Automated QA:** compile, unit, integration, lint, dependency check, dan deterministic regression test lulus di CI.
3. **Security review:** threat model diperbarui; Bandit, dependency audit, secret policy gate, container scan, dan manual authorization/privacy review lulus.
4. **Docker verification:** Compose valid, image dapat dibangun bersih, berjalan non-root/read-only, FFmpeg tersedia, dan tidak mengandung secret.
5. **Staging:** deploy dengan token staging; smoke test connect/play/control/disconnect di minimal dua guild; simpan hasil tanpa query/judul/user content.
6. **Observability:** health, privacy-safe metrics, structured logging, alert, retention, dan redaction diuji sebelum beta.
7. **Closed beta:** tester dan durasi disetujui; consent/feedback channel tersedia; severity tinggi menghentikan beta.
8. **Release candidate:** tag immutable, SBOM/image digest, changelog, rollback artifact, dan seluruh gate sebelumnya terhubung ke satu commit.
9. **Production:** approval manusia wajib; canary satu instance/guild group, evaluasi metrics, lalu rollout bertahap.
10. **Monitoring/maintenance:** on-call owner, alert response, backup/restore drill, dependency update, incident review, dan jadwal patch aktif.

## Evidence minimum

Setiap tahap menambahkan entri bertanggal ke `changelog.md` berisi commit/tag, environment, perintah atau workflow run, hasil, approver (untuk external deployment), rollback target, dan risiko tersisa. Secret, query, judul lagu, isi pesan, direct stream URL, serta ID user mentah dilarang menjadi evidence.

## Stop conditions

AI harus berhenti dan meminta operator bila memerlukan secret, akses registry/host, persetujuan legal/provider, pembuatan environment berbayar, tester manusia, atau keputusan rollout. Kegagalan security severity medium/high, kebocoran secret, cross-guild state, atau voice privacy violation memblokir release.
