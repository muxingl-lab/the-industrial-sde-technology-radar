# FAISS Source Study — Level 1: Philosophy

[Radar home](../README.md) · [FAISS home](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

Level 1 begins with a retrieval service, requests, vectors, memory, and latency. The goal is to recognize the engineering problem before recalling a FAISS class name.

## Q1. Why must an approximate retrieval system keep an exact baseline?

**Starting point.** A recommendation service receives a query vector and must return the nearest items from millions of candidates. A full scan is too expensive for every production request, so the team introduces an approximate index.

**What breaks.** Once the scan disappears, latency may improve while relevance quietly degrades. Production clicks are delayed and confounded signals; they cannot tell whether a specific index configuration missed the neighbors it should have returned.

**The question.** What trusted result lets the team measure what the faster path omitted?

**Philosophy:** optimization needs an oracle. Preserve exact top-k search on a representative evaluation corpus, then measure recall, latency, and cost against it.

**Think of:** reference implementations, differential tests, shadow traffic, golden data sets.

**FAISS example:** a flat index provides exact search and ground-truth neighbors for evaluating IVF, HNSW, or compressed indexes.

**Warning:** a baseline built from unrepresentative queries can certify the wrong system.

[Go deeper](level-2-internals.md#q1-exact-baseline) · [Implement it](level-3-code-labs.md#q1-exact-top-k-and-recall)

## Q2. How should a service budget recall, latency, and bytes per vector?

**Starting point.** The same index can search more candidates for better recall, compress vectors to fit more data, or batch requests for throughput. None of these settings is free.

**What breaks.** “Use approximate nearest neighbors” is not a specification. A configuration can win a microbenchmark while violating the product's relevance floor, tail-latency SLO, or memory ceiling.

**The question.** Which quality loss is allowed, under which workload, in exchange for which resource savings?

**Philosophy:** approximation is a contract with at least three axes: answer quality, resource cost, and latency distribution. Tune on a Pareto frontier, not a single score.

**Think of:** error budgets, load envelopes, quality gates, cost-per-query.

**FAISS example:** `nprobe`, HNSW `efSearch`, PQ code size, and batch size expose different positions on that frontier.

**Warning:** average latency and average recall can hide bad query cohorts.

[Go deeper](level-2-internals.md#q2-quality-and-resource-budget) · [Implement it](level-3-code-labs.md#q2-budgeted-configuration-selection)

## Q3. How can an inverted index search less data while retaining a quality control?

**Starting point.** Most vectors are irrelevant to one query. If vectors are grouped by a coarse representative, the request can first choose promising groups and scan only their members.

**What breaks.** Searching too few groups misses neighbors near partition boundaries. Searching every group recreates a full scan and pays extra indirection.

**The question.** How should the system partition candidates and choose how many partitions each request probes?

**Philosophy:** spend a cheap routing decision to avoid expensive fine-grained work, while keeping the fan-out explicit and measurable.

**FAISS example:** IVF assigns vectors to coarse centroids, stores IDs and codes in inverted lists, and searches `nprobe` selected lists.

**Warning:** skewed lists turn a fixed partition count into unpredictable work.

[Go deeper](level-2-internals.md#q3-inverted-file-search) · [Implement it](level-3-code-labs.md#q3-miniature-ivf)

## Q4. When should graph traversal replace scanning candidate lists?

**Starting point.** A query may benefit from following local neighbor links rather than choosing independent buckets. Search begins at an entry point and expands promising vertices until its budget is exhausted.

**What breaks.** Sparse or poorly constructed links reduce reachability; broad traversal consumes memory and random accesses. Inserts also change graph quality.

**The question.** When does adaptive, query-dependent exploration justify graph memory and construction cost?

**Philosophy:** indexes exchange predictable sequential work for selective pointer chasing. Choose using measured data geometry, update rate, and hardware locality.

**FAISS example:** HNSW uses a layered proximity graph and a bounded candidate frontier.

**Warning:** graph recall depends on both build-time and search-time breadth.

[Go deeper](level-2-internals.md#q4-graph-search) · [Implement it](level-3-code-labs.md#q4-bounded-best-first-search)

## Q5. When should vectors be compressed, and how should quantization loss be measured?

**Starting point.** Keeping every vector as 32-bit floats may exceed RAM or memory bandwidth. Short codes let more candidates fit in fast memory and make scans cheaper.

**What breaks.** Compression changes distances. A small reconstruction error can still reorder the top-k candidates that matter to the product.

**The question.** Which representation preserves enough ranking quality for the memory and bandwidth it saves?

**Philosophy:** physical representation is part of the query plan. Evaluate it using downstream neighbor recall, not only reconstruction error.

**FAISS example:** product quantization splits a vector into subspaces and stores one centroid ID per subspace.

**Warning:** codebooks trained on stale or biased samples encode that bias into every result.

[Go deeper](level-2-internals.md#q5-product-quantization) · [Implement it](level-3-code-labs.md#q5-product-quantization-core)

## Q6. How should training data and distribution drift affect an index?

**Starting point.** IVF centroids and PQ codebooks are learned from a sample, while production vectors and queries continue to change.

**What breaks.** An index can remain mechanically healthy but route new data into overloaded lists or represent it with growing error. Rebuilding too often wastes resources and complicates publication.

**The question.** Which measurements should trigger retraining, and how can a new generation be validated before serving?

**Philosophy:** a trained index is a versioned model artifact. Record its data window, evaluate drift, and promote only after quality and operational checks.

**FAISS example:** trained indexes expose an explicit `train` phase before `add` and `search`.

**Warning:** successful serialization proves compatibility, not relevance quality.

[Go deeper](level-2-internals.md#q6-training-and-drift) · [Implement it](level-3-code-labs.md#q6-drift-trigger)

## Q7. When should search state live on CPU versus GPU?

**Starting point.** GPUs offer high arithmetic and memory bandwidth, but vectors and requests may begin on the CPU. Transfer, batching, replication, and device memory become part of request latency.

**What breaks.** Moving a tiny query to a GPU can cost more than searching it on the CPU. Copying a large index to every device may exceed capacity; batching too long hurts tail latency.

**The question.** Which data and work should cross the device boundary, at what batch size, and with what fallback?

**Philosophy:** place computation where the entire data path is cheapest. Include transfer, queueing, memory residency, and failure recovery in the model.

**FAISS example:** CPU and GPU index implementations can trade host-device transfer for accelerator throughput.

**Warning:** peak throughput is not per-request latency under bursty traffic.

[Go deeper](level-2-internals.md#q7-cpugpu-placement) · [Implement it](level-3-code-labs.md#q7-placement-cost-model)

## Q8. How should a serving system replace a rebuilt index without exposing a partial generation?

**Starting point.** Training, adding vectors, and serializing a large index may take hours. Requests must continue using the old generation during the build.

**What breaks.** Mutating the live object can expose partial state. Replacing several files independently can mix generations. Loading before validation can exhaust memory or make rollback slow.

**The question.** How can the service construct, validate, publish, and retire an index as one generation change?

**Philosophy:** build immutable replacement state off-path, validate it, switch one authoritative pointer or manifest atomically, and retain the previous generation until readers drain.

**FAISS example:** index I/O supplies serialization; the surrounding service must supply generation identity and cutover.

**Warning:** FAISS does not turn serialization into a distributed deployment protocol.

[Go deeper](level-2-internals.md#q8-generation-publication) · [Implement it](level-3-code-labs.md#q8-generation-manager)
