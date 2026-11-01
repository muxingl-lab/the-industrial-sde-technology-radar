# Valkey Technology Radar

[Radar home](../README.md)

Source baseline: [Valkey `9.1.3`](https://github.com/valkey-io/valkey/tree/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8), commit `29173b67508b2de4c0f0ed551f3b47cf19fc3ca8`. Studied 2026-10-31.

This volume does not restate the Redis volume. It studies mechanisms that are prominent in the pinned Valkey source and uses the shared problem library where the two systems overlap.

## Reading paths

- [Level 1 — Philosophy and problem recognition](level-1-philosophy.md)
- [Level 2 — Internals, workflows, and interview follow-ups](level-2-internals.md)
- [Level 3 — Code labs and handwritten implementations](level-3-code-labs.md)

## Core problem families

1. Parallel connection work with single-owner command semantics
2. Software prefetch across independent commands
3. Snapshot transfer concurrent with replication catch-up
4. Atomic online migration of slot ranges
5. Fine-grained expiration inside aggregate values

## Source map

| Concern | Active source and tests |
|---|---|
| Adaptive I/O workers and handoff | [`src/io_threads.c`](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/src/io_threads.c), [`tests/unit/io-threads.tcl`](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/tests/unit/io-threads.tcl) |
| Command/key prefetch | [`src/memory_prefetch.c`](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/src/memory_prefetch.c) |
| Dual-channel synchronization | [`src/replication.c`](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/src/replication.c), [`tests/integration/dual-channel-replication.tcl`](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/tests/integration/dual-channel-replication.tcl) |
| Atomic slot migration | [`src/cluster_migrateslots.c`](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/src/cluster_migrateslots.c), [`tests/unit/cluster/cluster-migrateslots.tcl`](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/tests/unit/cluster/cluster-migrateslots.tcl) |
| Hash-field expiration index | [`src/vset.c`](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/src/vset.c), [`src/expire.c`](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/src/expire.c), [`tests/unit/hashexpire.tcl`](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/tests/unit/hashexpire.tcl) |
