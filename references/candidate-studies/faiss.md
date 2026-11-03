# FAISS Candidate Study

[Roadmap](../../ROADMAP.md) · [Problem library](../../library/README.md) · [Pattern registry](../../library/patterns.json)

## Provenance

- Upstream: [`facebookresearch/faiss`](https://github.com/facebookresearch/faiss)
- Inspected revision: [`b80093c5b290578ed7de1975583e295309b4de81`](https://github.com/facebookresearch/faiss/tree/b80093c5b290578ed7de1975583e295309b4de81)
- Study date: 2026-11-02
- Status: roadmap admission study, not a pinned book volume

The revision records what was inspected. A future volume must select a released tag and repeat the active-path check.

## Admission decision

FAISS adds a missing architecture family: vector similarity search under an explicit quality budget. Redis already teaches approximation, and vLLM and SGLang already teach accelerator memory and batching. FAISS connects those ideas, but its central decision is different: which candidates may the search skip while still meeting a measured recall target?

The candidate passes the roadmap admission test because its public `Index` contract, index families, tests, and CPU/GPU implementations can support all three learning levels without reducing the volume to API names.

## Verified source map

| Concern | Active evidence | Engineering lesson |
|---|---|---|
| Public lifecycle | [`faiss/Index.h`](https://github.com/facebookresearch/faiss/blob/b80093c5b290578ed7de1975583e295309b4de81/faiss/Index.h) | Training, addition, search, reconstruction, and removal are distinct lifecycle operations; not every index supports each one equally. |
| Inverted-file search | [`faiss/IndexIVF.h`](https://github.com/facebookresearch/faiss/blob/b80093c5b290578ed7de1975583e295309b4de81/faiss/IndexIVF.h) and [`IndexIVF.cpp`](https://github.com/facebookresearch/faiss/blob/b80093c5b290578ed7de1975583e295309b4de81/faiss/IndexIVF.cpp) | A coarse quantizer selects inverted lists. `nprobe` turns recall versus scanned work into a request-time budget. |
| Compressed representation | [`faiss/IndexIVFPQ.h`](https://github.com/facebookresearch/faiss/blob/b80093c5b290578ed7de1975583e295309b4de81/faiss/IndexIVFPQ.h) | Product-quantized codes trade bytes and distance accuracy for capacity and scan speed. |
| Graph search | [`faiss/IndexHNSW.h`](https://github.com/facebookresearch/faiss/blob/b80093c5b290578ed7de1975583e295309b4de81/faiss/IndexHNSW.h) | A navigable graph spends memory and build work to reduce query exploration. |
| Mutable lookup support | [`faiss/invlists/DirectMap.h`](https://github.com/facebookresearch/faiss/blob/b80093c5b290578ed7de1975583e295309b4de81/faiss/invlists/DirectMap.h) | Mapping an external ID back to an inverted-list position enables reconstruction and removal but adds state and update constraints. |
| Accuracy contract | [`tests/test_index_accuracy.py`](https://github.com/facebookresearch/faiss/blob/b80093c5b290578ed7de1975583e295309b4de81/tests/test_index_accuracy.py) and [`tests/test_hnsw.py`](https://github.com/facebookresearch/faiss/blob/b80093c5b290578ed7de1975583e295309b4de81/tests/test_hnsw.py) | Approximate indexes are tested against exact or intact baselines through recall, not through latency alone. |
| Persistence boundary | [`faiss/index_io.h`](https://github.com/facebookresearch/faiss/blob/b80093c5b290578ed7de1975583e295309b4de81/faiss/index_io.h) and [`tests/test_io.py`](https://github.com/facebookresearch/faiss/blob/b80093c5b290578ed7de1975583e295309b4de81/tests/test_io.py) | An index has a serialized generation and compatibility surface; publishing a replacement remains an application-level protocol. |

## Representative workflow

An IVF-based deployment first trains a coarse quantizer, and possibly a second encoder, on representative vectors. Adding a vector assigns it to a coarse list and stores an ID plus either the vector or a compressed code. A query searches the coarse quantizer, selects up to `nprobe` lists, prefetches those lists, scans their codes, and keeps the best candidates. Increasing `nprobe` searches more data and can improve recall, but consumes more memory bandwidth and CPU or GPU work.

This flow creates two distinct correctness questions. The library must preserve index structure and ID mappings. The application must decide whether the returned approximation is good enough and how a newly trained index generation replaces the old one without mixing incompatible codebooks or serving a partial build.

## Overlap audit

| Candidate problem | Existing radar relationship | Classification | Boundary |
|---|---|---|---|
| Search less data under a quality budget | Redis Q4 approximation | Same philosophy, different error contract | Redis estimates an aggregate with bounded statistical error; FAISS may omit true neighbors and must measure recall against exact results. |
| Change physical representation to fit more state | Redis Q2 adaptive representation | Same problem, different constraints | Redis changes representation as one collection changes size; FAISS selects trained vector codes and index layouts for a dataset and workload. |
| Batch work on accelerators | vLLM Q2 and SGLang Q2 | Neighboring problem | Inference schedulers own request lifecycles; FAISS batches independent searches and memory transfers without token-generation state. |
| Map logical IDs to physical storage | vLLM Q1 and SGLang Q9 memory indirection | Neighboring problem | FAISS direct maps support reconstruction and mutation; inference block maps protect live per-request state. |
| Route toward likely useful state | SGLang Q8 locality-aware routing | Neighboring problem | ANN traversal prunes a search space inside an index; replica routing chooses an execution owner across servers. |
| Publish a rebuilt generation | Redis Q9 rewrite and atomic switch | Same problem, different artifact | Both require building replacement state away from readers and switching generations; FAISS does not supply the full serving cutover protocol. |

No existing comparison chapter should receive a FAISS member before the full volume defines stable question identities. The strongest future comparison candidates are approximation contracts, adaptive representation, and atomic generation replacement.

## Candidate question boundary

1. When is exhaustive search the right baseline even if it cannot be the final serving design?
2. How should a service turn recall, latency, and bytes per vector into an explicit approximation budget?
3. How does an inverted file reduce scanned work, and what should control the number of probed lists?
4. When should a system spend memory on a navigable graph instead of spending query work on more candidates?
5. When should vectors be compressed, and how should quantization error be measured against product loss?
6. How should training data represent future traffic, and what signals show that centroids or codebooks have drifted?
7. Which index state belongs on the CPU or GPU, and when does transfer cost dominate computation?
8. How should additions, removals, filtering, serialization, and generation replacement work when the index is not a transactional database?

## Claims deliberately excluded

- No universal claim that one index family is fastest.
- No benchmark claim without a pinned dataset, hardware profile, recall target, and concurrency level.
- No claim that FAISS provides a complete distributed vector database or atomic online index deployment.
- No assumption that a GPU index wins when inputs and outputs cross the host-device boundary for every request.
