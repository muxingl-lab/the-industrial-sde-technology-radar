# Feast Technology Radar

[Radar home](../README.md) · [Source map](source-map.md)

Source baseline: [Feast](https://github.com/feast-dev/feast) `v0.67.0`, commit `2dfb9e6d1a37719fd11028d916094050f1cdd552`.

## Reading paths

- [Level 1 — Philosophy and problem recognition](level-1-philosophy.md)
- [Level 2 — Internals, workflows, and interview follow-ups](level-2-internals.md)
- [Level 3 — Code labs and handwritten implementations](level-3-code-labs.md)

## Core problem families

1. Point-in-time-correct historical retrieval
2. One feature contract across offline and online paths
3. Resumable offline-to-online materialization
4. Out-of-order online updates
5. Transformation placement and parity
6. Metadata and infrastructure rollout
7. Backend capability boundaries
8. Cross-store writes and recovery
9. Freshness and correctness observability

Feast supplies definitions, orchestration, and provider interfaces. It does not make every backend transactional or automatically eliminate training-serving skew.
