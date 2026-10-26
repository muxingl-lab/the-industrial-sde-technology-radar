# Redis Technology Radar

[Radar home](../README.md)

Source baseline: Redis `8.8.3`, commit `76ec1c311045cf2f28332a95631259cc67ad4b51`.

## Reading paths

- [Level 1 — Philosophy and problem recognition](level-1-philosophy.md)
- [Level 2 — Internals, workflows, and interview follow-ups](level-2-internals.md)
- [Level 3 — Code labs and handwritten implementations](level-3-code-labs.md)

## Core problem families

1. Incremental work and latency budgets
2. Adaptive data representation
3. Multiple indexes for multiple access paths
4. Approximation and sampling
5. Logical deletion and deferred reclamation
6. State ownership and safe background work
7. Expiration and bounded maintenance
8. Snapshotting with copy-on-write
9. Log compaction and atomic replacement
10. Incremental recovery with identity, offset, and bounded history
11. Backpressure and slow consumers
12. Sharding and online migration
13. Failure suspicion and distributed decisions
14. Atomicity boundaries and idempotency
