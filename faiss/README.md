# FAISS Technology Radar

[Radar home](../README.md) · [Source map](source-map.md)

Source baseline: [FAISS](https://github.com/facebookresearch/faiss) `v1.15.1`, commit `75c755c5a1fc854756aaf3bd1131213aeb21d8d1`.

## Reading paths

- [Level 1 — Philosophy and problem recognition](level-1-philosophy.md)
- [Level 2 — Internals, workflows, and interview follow-ups](level-2-internals.md)
- [Level 3 — Code labs and handwritten implementations](level-3-code-labs.md)

## Core problem families

1. Exact baselines for approximate retrieval
2. Explicit recall, latency, and memory budgets
3. Inverted-file candidate pruning
4. Graph traversal for adaptive search
5. Vector compression and quantization error
6. Training data, distribution drift, and rebuilds
7. CPU/GPU placement and batching
8. Safe publication of rebuilt index generations

FAISS is an index library, not a complete distributed vector database. The volume therefore separates index mechanics from the serving system that must own replication, admission, durability, and cutover.
