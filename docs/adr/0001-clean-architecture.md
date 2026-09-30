# ADR-0001: Clean Architecture with Guild-Isolated State

Status: accepted  
Date: 2026-09-30

## Context

Versi awal menyatukan config, Discord events, media resolution, queue, dan voice player dalam satu file. Satu `MusicManager` global menyebabkan risiko state lintas guild dan membuat logic sulit diuji tanpa Discord/network.

## Decision

Proyek memakai empat area:

1. Domain entities dan queue rules.
2. Application use cases dan integration ports.
3. Discord/media adapters.
4. Composition root untuk config serta dependency wiring.

Queue, lock, player, current track, dan idle task dibatasi oleh `guild_id`. Adapter boleh bergantung pada application/domain, tetapi arah sebaliknya dilarang.

## Consequences

Positif:

- Unit test cepat tanpa Discord atau internet.
- Provider dan persistence dapat diganti melalui port.
- State dan concurrency ownership lebih jelas.
- Risiko cross-guild berkurang secara struktural.

Trade-off:

- Jumlah file bertambah.
- Mapping error dan lifecycle adapter perlu disiplin.
- Integration test tetap diperlukan untuk menjamin perilaku voice sebenarnya.

## Rejected Alternatives

- Mempertahankan satu file: sederhana tetapi tidak scalable dan sulit diuji.
- Global manager dengan dictionary internal saja: memperbaiki sebagian state, tetapi tetap mencampur domain, vendor, dan UI.
- Framework dependency-injection tambahan: belum sebanding dengan ukuran proyek; composition root manual lebih jelas.
