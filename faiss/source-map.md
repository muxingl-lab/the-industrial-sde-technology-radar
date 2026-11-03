# FAISS Source Map

[FAISS home](README.md) · [Level 1](level-1-philosophy.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

This volume was audited against FAISS `v1.15.1` at commit `75c755c5a1fc854756aaf3bd1131213aeb21d8d1`. Links are pinned so later refactors cannot silently change the evidence.

| Concern | Primary source | What to inspect |
|---|---|---|
| Index lifecycle | [`faiss/Index.h`](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/faiss/Index.h) | `train`, `add`, `search`, reconstruction, deletion, and `is_trained` |
| IVF search | [`faiss/IndexIVF.h`](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/faiss/IndexIVF.h) | Coarse quantizer, inverted lists, `nprobe`, list scanning, and prefetch |
| Compressed codes | [`faiss/IndexIVFPQ.h`](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/faiss/IndexIVFPQ.h) | Product-quantized codes and asymmetric distance computation |
| Graph search | [`faiss/IndexHNSW.h`](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/faiss/IndexHNSW.h) | HNSW graph ownership, construction, and search parameters |
| Mutation lookup | [`faiss/invlists/DirectMap.h`](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/faiss/invlists/DirectMap.h) | Mapping external IDs back to physical list positions |
| Persistence | [`faiss/index_io.h`](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/faiss/index_io.h) | Serialization boundaries and index loading |
| Quality tests | [`tests/test_index_accuracy.py`](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/tests/test_index_accuracy.py) | Comparing approximate results with an exact reference |
| I/O tests | [`tests/test_io.py`](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/tests/test_io.py) | Round trips and serialized index behavior |

## Boundary decisions

- Recall claims require an exact ground truth on representative queries.
- `nprobe`, HNSW search breadth, and code size are workload controls, not universal constants.
- Training and serving are different lifecycle phases; a trained index carries assumptions about its sample distribution.
- A direct map buys reconstruction and mutation support at a memory and maintenance cost.
- Serialization produces an artifact. Atomic deployment, rollback, replication, and request draining belong to the surrounding service.

## Cross-system audit

FAISS and Redis both trade exact work for bounded resource use, but the error contracts differ: Redis sketches estimate aggregates, while ANN search may omit a true neighbor. FAISS index publication resembles Redis AOF generation replacement because both build replacement state away from readers and then switch an authoritative generation. Accelerator batching is adjacent to vLLM and SGLang scheduling, but FAISS searches do not own an autoregressive request lifecycle.
