# SGLang — Level 2: Internals and Interviews
[Radar](../README.md) · [SGLang](README.md) · [Level 1](level-1-philosophy.md) · [Level 3](level-3-code-labs.md)

## Q1. Radix prefix cache
[Philosophy](level-1-philosophy.md#q1-how-can-the-server-find-the-longest-shared-beginning-between-requests) · [Lab](level-3-code-labs.md#q1-radix-prefix-cache)

`RadixCache` walks token segments for longest-prefix match, splitting nodes on partial matches and associating paths with KV indices. Active paths are protected; eviction targets unreferenced leaves under policy. Follow-ups: O(prefix) lookup, compressed edges, partial splits, reference/lock propagation, session isolation, and why radix structure captures sharing better than whole-prompt hashes. Source: [`radix_cache.py`](https://github.com/sgl-project/sglang/blob/baa9befa381511cd4d56f83980951e5a45fffc6d/python/sglang/srt/mem_cache/radix_cache.py).

## Q2. Continuous scheduling
[Philosophy](level-1-philosophy.md#q2-how-are-asynchronous-requests-continuously-batched) · [Lab](level-3-code-labs.md#q2-request-scheduler)

The scheduler receives typed requests, matches reusable prefixes, forms prefill/decode batches, runs TP workers, processes results, streams output, and releases or caches state. Requests transition through explicit lifecycle states. Follow-ups: fairness, retraction, abort races, batch merge, memory checks, and why scheduler ownership simplifies consistency. Source: [`scheduler.py`](https://github.com/sgl-project/sglang/blob/baa9befa381511cd4d56f83980951e5a45fffc6d/python/sglang/srt/managers/scheduler.py).

## Q3. Chunked prefill
[Philosophy](level-1-philosophy.md#q3-how-can-long-inputs-share-the-gpu-with-active-output-streams) · [Lab](level-3-code-labs.md#q3-prefill-controller)

Prefill admission consumes a token/memory budget; long prompts can be chunked, and dynamic sizing reacts to available capacity and running decode pressure. Follow-ups: TTFT versus ITL, mixed-batch kernels, starvation, conservative memory estimation, and feedback instability in dynamic chunk sizing.

## Q4. Hierarchical cache
[Philosophy](level-1-philosophy.md#q4-how-should-reusable-model-state-move-across-gpu-host-memory-and-storage) · [Lab](level-3-code-labs.md#q4-tiered-cache)

HiCache coordinates device pools, host pools, and pluggable storage. Metadata tracks residency and transfer state; promotion/demotion must not expose incomplete blocks. Decide using expected reuse benefit minus transfer and occupancy cost. Follow-ups: inclusive versus exclusive tiers, async transfer, eviction ordering, checksum/identity, backpressure, and cache pollution. Source: [`hicache_design.mdx`](https://github.com/sgl-project/sglang/blob/baa9befa381511cd4d56f83980951e5a45fffc6d/docs/docs/advanced_features/hicache_design.mdx).

## Q5. PD disaggregation
[Philosophy](level-1-philosophy.md#q5-when-should-input-processing-and-token-generation-use-separate-worker-fleets) · [Lab](level-3-code-labs.md#q5-kv-transfer)

Prefill workers compute prompt KV, publish transfer metadata, and move blocks through a connector/staging protocol; decode workers validate readiness and continue generation. The routing/control plane must bind request, model, layout, and generation. Follow-ups: transfer overlap, retries, duplicate delivery, timeout cleanup, decode admission before KV arrival, and when network cost outweighs specialization. Source: [`disaggregation`](https://github.com/sgl-project/sglang/tree/baa9befa381511cd4d56f83980951e5a45fffc6d/python/sglang/srt/disaggregation).

## Q6. Constrained decoding
[Philosophy](level-1-philosophy.md#q6-how-is-schema-conforming-output-guaranteed) · [Lab](level-3-code-labs.md#q6-grammar-mask)

A grammar backend compiles schema/regex into state; each step derives allowed token IDs and masks logits before sampling; accepted tokens advance grammar state. Jump-forward uses deterministic continuation when grammar state permits. Follow-ups: tokenizer byte boundaries, compilation caching, empty masks, reasoning-model structure, rollback with speculation, and why post-hoc validation wastes work. Source: [`constrained`](https://github.com/sgl-project/sglang/tree/baa9befa381511cd4d56f83980951e5a45fffc6d/python/sglang/srt/constrained).

## Q7. Adaptive speculation
[Philosophy](level-1-philosophy.md#q7-how-far-ahead-should-a-cheaper-predictor-be-allowed-to-work) · [Lab](level-3-code-labs.md#q7-speculation-controller)

Draft work proposes multiple tokens; target verification commits an accepted prefix. An adaptive controller changes depth from recent acceptance and cost signals. Follow-ups: controller hysteresis, workload phase changes, memory cost, structured-output interaction, and optimizing saved target latency rather than acceptance alone.

## Q8. Routing and parallelism
[Philosophy](level-1-philosophy.md#q8-how-should-replicas-be-selected-when-both-load-and-cache-locality-matter) · [Lab](level-3-code-labs.md#q8-locality-router)

TP/PP/EP partition one execution; DP replicas provide independent capacity. Routing can combine published queue/load with prefix affinity. Follow-ups: stale telemetry, herd behavior, consistent hashing, hysteresis, expert imbalance, topology-aware collectives, and separating replica routing from intra-replica parallelism.

## Q9. Memory-pool indirection
[Philosophy](level-1-philosophy.md#q9-how-should-logical-token-positions-map-to-reusable-physical-memory-slots) · [Lab](level-3-code-labs.md#q9-token-slot-pool)

Request/token pools map logical positions to KV slots; device pools own physical layouts. Allocation happens before execution, rollback restores all partially reserved slots, and completion either caches or frees them. Follow-ups: fragmentation, free lists, multimodal/hybrid layouts, quantized KV, and invariant checks preventing duplicate ownership. Source: [`memory_pool.py`](https://github.com/sgl-project/sglang/blob/baa9befa381511cd4d56f83980951e5a45fffc6d/python/sglang/srt/mem_cache/memory_pool.py).

## Q10. Serving pipeline
[Philosophy](level-1-philosophy.md#q10-how-does-a-multi-process-serving-pipeline-preserve-ownership) · [Lab](level-3-code-labs.md#q10-fenced-pipeline)

Tokenizer manager owns API-facing preprocessing, scheduler owns lifecycle and allocation, TP workers own device execution, detokenizer owns text reconstruction, and output components stream results. Typed IPC and request IDs connect stages. Follow-ups: bounded queues, worker restart, stale generation fencing, cancellation propagation, tokenizer CPU saturation, and stage-level metrics.
