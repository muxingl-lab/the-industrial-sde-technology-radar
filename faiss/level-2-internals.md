# FAISS Source Study — Level 2: Internals and Interviews

[Radar home](../README.md) · [FAISS home](README.md) · [Level 1](level-1-philosophy.md) · [Level 3](level-3-code-labs.md) · [Source map](source-map.md)

Level 2 explains the end-to-end workflow, its owner, its invariant, and the failure modes a senior-SDE interview should uncover.

## Q1. Exact baseline

[Philosophy](level-1-philosophy.md#q1-why-must-an-approximate-retrieval-system-keep-an-exact-baseline) · [Code lab](level-3-code-labs.md#q1-exact-top-k-and-recall)

An exact flat index stores all vectors and computes every query-to-vector distance before selecting top-k. Build a frozen evaluation set from representative vectors and queries, compute ground truth with the same metric and filtering rules as production, and version it with the corpus. Every approximate candidate is evaluated against those neighbor IDs.

**Invariant:** the oracle and candidate must agree on vector preprocessing, distance metric, eligible corpus, tie handling, and k. Recall@k is meaningless if either path normalizes vectors differently.

**Follow-ups.** Exact evaluation can be offline, sampled, sharded, or run on shadow traffic. Add per-cohort recall, rank-sensitive metrics, and business reranker metrics. Refresh the corpus when data drifts, but preserve older suites to detect regressions.

## Q2. Quality and resource budget

[Philosophy](level-1-philosophy.md#q2-how-should-a-service-budget-recall-latency-and-bytes-per-vector) · [Code lab](level-3-code-labs.md#q2-budgeted-configuration-selection)

Benchmark configurations across query cohorts and concurrency levels. Record recall@k, P50/P99 latency, resident bytes per vector, build time, update cost, and throughput. Reject any configuration that violates a hard constraint; select among the survivors using cost or latency. Store the chosen knobs beside the index generation.

**Invariant:** quality is tested at the same operational envelope in which the index will serve. Increasing concurrent load, filtering, or list skew must not silently move the configuration outside its certified region.

**Follow-ups.** `nprobe` and `efSearch` can be dynamic per request, but the API must expose a maximum budget. Tail cohorts matter more than a global average. Rebenchmark after compiler, hardware, corpus, or embedding-model changes.

## Q3. Inverted-file search

[Philosophy](level-1-philosophy.md#q3-how-can-an-inverted-index-search-less-data-while-retaining-a-quality-control) · [Code lab](level-3-code-labs.md#q3-miniature-ivf) · [IndexIVF](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/faiss/IndexIVF.h)

Training learns `nlist` coarse centroids. Adding a vector assigns it to a centroid and appends its ID plus raw or compressed code to that list. Search first asks the coarse quantizer for the nearest `nprobe` centroids, prefetches their lists, scans their members, and maintains the global top-k heap.

**Invariant:** every stored ID is reachable from its assigned list, list metadata and codes move together, and the metric used for coarse selection is compatible with fine scoring.

**Follow-ups.** More lists reduce average scan size but increase training and routing overhead. `nprobe` controls recall and work only indirectly because list sizes are skewed. Filters can cause underfilled results, requiring oversampling or filter-aware indexes. A direct map is optional because reverse lookup costs memory.

## Q4. Graph search

[Philosophy](level-1-philosophy.md#q4-when-should-graph-traversal-replace-scanning-candidate-lists) · [Code lab](level-3-code-labs.md#q4-bounded-best-first-search) · [IndexHNSW](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/faiss/IndexHNSW.h)

HNSW builds a multilayer proximity graph. Search greedily descends sparse upper layers to find a useful region, then runs a wider best-first exploration at the dense base layer. `efConstruction` spends work on graph quality; `efSearch` bounds the query frontier.

**Invariant:** visited state prevents cycles, the candidate frontier is ordered by promise, and the retained-result frontier supplies a stopping condition. IDs must remain aligned with the storage index the graph wraps.

**Follow-ups.** HNSW often offers high recall but adds graph bytes and irregular memory access. Deletes and high update rates require tombstones or rebuild policy. Hybrid designs can put HNSW on IVF centroids or use graph routing with compressed storage.

## Q5. Product quantization

[Philosophy](level-1-philosophy.md#q5-when-should-vectors-be-compressed-and-how-should-quantization-loss-be-measured) · [Code lab](level-3-code-labs.md#q5-product-quantization-core) · [IndexIVFPQ](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/faiss/IndexIVFPQ.h)

PQ divides each d-dimensional vector into m sub-vectors. Each subspace learns a small codebook; encoding stores one centroid ID per subspace. At query time, asymmetric distance computation builds a query-to-codeword lookup table and scores a database code with m table reads and additions. IVF-PQ can encode residuals relative to the coarse centroid.

**Invariant:** the codebook version, subspace layout, metric, and encoded bytes belong to one index generation. Decoding with a different codebook is corruption, not graceful degradation.

**Follow-ups.** More bits improve fidelity but consume memory and bandwidth. Residual encoding improves local accuracy. Reranking a shortlist with full vectors can recover quality. Optimize end-to-end recall rather than mean squared reconstruction error alone.

## Q6. Training and drift

[Philosophy](level-1-philosophy.md#q6-how-should-training-data-and-distribution-drift-affect-an-index) · [Code lab](level-3-code-labs.md#q6-drift-trigger) · [Index lifecycle](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/faiss/Index.h)

Sample training vectors from the population the index will represent, train coarse centroids and codebooks, then add production vectors. Record embedding-model version, sample window, transforms, seeds, parameters, and evaluation results. Monitor list imbalance, quantization error, recall samples, and query/corpus drift. Build a new generation when a policy threshold is crossed.

**Invariant:** an index cannot accept operations that require learned state before `is_trained` is true, and vectors must use the same embedding dimension and preprocessing contract as training.

**Follow-ups.** Train/test leakage can make recall optimistic. Uniform sampling can underrepresent important tails. Incremental additions are not equivalent to retraining. A rebuild trigger needs hysteresis and a minimum interval to prevent churn.

## Q7. CPU/GPU placement

[Philosophy](level-1-philosophy.md#q7-when-should-search-state-live-on-cpu-versus-gpu) · [Code lab](level-3-code-labs.md#q7-placement-cost-model)

Model the path as queueing plus host preparation, host-to-device transfer, device search, device-to-host result transfer, and any reranking. Keep an index resident when repeated queries amortize upload cost. Batch enough work to saturate kernels without exceeding a queue-delay budget. Shard by vectors for capacity or replicate by device for throughput.

**Invariant:** result IDs preserve their global meaning across shards, and merging uses the same distance convention. Admission must cap device memory and queued batches.

**Follow-ups.** Pinned buffers and reusable GPU resources reduce allocation overhead. Small batches may favor CPU. Replication increases refresh cost. A GPU failure needs a capacity-aware fallback rather than an unbounded CPU queue.

## Q8. Generation publication

[Philosophy](level-1-philosophy.md#q8-how-should-a-serving-system-replace-a-rebuilt-index-without-exposing-a-partial-generation) · [Code lab](level-3-code-labs.md#q8-generation-manager) · [Index I/O](https://github.com/facebookresearch/faiss/blob/75c755c5a1fc854756aaf3bd1131213aeb21d8d1/faiss/index_io.h)

Build into a generation-specific location. Write the index and metadata, fsync or durably upload them, reload the artifact, run integrity and recall smoke tests, and mark the generation ready. Each server loads it under a memory budget, then atomically swaps one local pointer or a manifest reference. Reference counting or epochs keep the old object alive until in-flight readers finish.

**Invariant:** one request observes one complete generation. Artifact identity includes the index, metadata, embedding contract, and any external ID mapping.

**Follow-ups.** Budget peak memory for old plus new generations. Roll out gradually and retain rollback. Checksums catch corruption but not semantic mismatch. In a fleet, control-plane publication and per-host activation are distinct states.
