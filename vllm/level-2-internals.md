# vLLM — Level 2: Internals and Interviews
[Radar](../README.md) · [vLLM](README.md) · [Level 1](level-1-philosophy.md) · [Level 3](level-3-code-labs.md)

## Q1. Paged KV cache
[Philosophy](level-1-philosophy.md#q1-how-can-per-request-memory-grow-without-reserving-its-maximum-size) · [Lab](level-3-code-labs.md#q1-paged-kv-allocator)

The scheduler asks `KVCacheManager` for blocks; `BlockPool` owns free blocks, reference counts, and cached-block identity; worker block tables translate sequence positions for attention. Fixed blocks enable sharing and non-contiguous growth. Explain block-size trade-offs, hybrid attention cache groups, last-block waste, and why freeing a request must not free shared prefixes. Source: [`vllm/v1/core`](https://github.com/vllm-project/vllm/tree/5df63a7203cdb9328d824a27b682e77c7b9928be/vllm/v1/core).

## Q2. Continuous batching
[Philosophy](level-1-philosophy.md#q2-how-do-asynchronous-requests-share-the-gpu-efficiently) · [Lab](level-3-code-labs.md#q2-token-budget-scheduler)

Each engine step reconciles running and waiting requests against `max_num_scheduled_tokens`, sequence limits, KV availability, encoder work, and structured/speculative state. It emits a schedule consumed by the model runner, then applies outputs and frees finished state. Follow-ups: FCFS versus priority, starvation, token versus request budgets, and why iteration-level scheduling beats static batches. Source: [`scheduler.py`](https://github.com/vllm-project/vllm/blob/5df63a7203cdb9328d824a27b682e77c7b9928be/vllm/v1/core/sched/scheduler.py).

## Q3. Chunked prefill
[Philosophy](level-1-philosophy.md#q3-how-can-long-inputs-coexist-with-requests-that-need-one-quick-step) · [Lab](level-3-code-labs.md#q3-chunked-prefill)

Prompt work is capped by the remaining token budget; unfinished prefill remains schedulable next iteration while decode requests progress. Choose chunk size from TTFT/ITL objectives, launch efficiency, and memory. Follow-ups: head-of-line blocking, decode prioritization, starvation prevention, and why prefill is compute-heavy while decode is commonly bandwidth/KV-heavy.

## Q4. Prefix caching
[Philosophy](level-1-philosophy.md#q4-when-is-prefix-computation-safely-reusable) · [Lab](level-3-code-labs.md#q4-prefix-cache)

Only full blocks are safely content-addressed. A block hash incorporates parent hash, tokens, and relevant extra keys; cache lookup returns the longest block-aligned match. Shared blocks use reference counts and become evictable only when unreferenced. Follow-ups: hash collision defense, cache isolation, LRU metadata, invalidation after model/adapter change, and why partial final blocks are awkward. Source: [`prefix_caching.md`](https://github.com/vllm-project/vllm/blob/5df63a7203cdb9328d824a27b682e77c7b9928be/docs/design/prefix_caching.md).

## Q5. Admission and preemption
[Philosophy](level-1-philosophy.md#q5-what-happens-when-active-requests-need-more-accelerator-memory-than-exists) · [Lab](level-3-code-labs.md#q5-admission-control)

Allocation is a reservation decision: schedule only work whose KV blocks and other cache needs can be satisfied. When capacity fails, requests may be preempted and recomputed later. Correctness requires atomic rollback of scheduled resources. Follow-ups: recompute versus CPU swap, queue limits, tenant quotas, preemption priority, and thrash signals such as repeated preemption and low useful-token throughput.

## Q6. Speculative decoding
[Philosophy](level-1-philosophy.md#q6-how-can-cheap-predictions-reduce-calls-to-an-expensive-model) · [Lab](level-3-code-labs.md#q6-speculate-and-verify)

A proposer emits candidate tokens; the target evaluates them in parallel; acceptance/rejection sampling preserves the target distribution and commits only the accepted prefix plus a correction token. Evaluate proposer latency, acceptance length, verification batch cost, and extra KV/state. Follow-ups: greedy versus sampling correctness, n-gram versus draft models, adaptive depth, and metrics beyond acceptance rate. Source: [`spec_decode`](https://github.com/vllm-project/vllm/tree/5df63a7203cdb9328d824a27b682e77c7b9928be/vllm/v1/spec_decode).

## Q7. Parallelism
[Philosophy](level-1-philosophy.md#q7-which-parallelism-dimension-should-scale-the-model) · [Lab](level-3-code-labs.md#q7-parallelism-planner)

Tensor parallel shards per-layer math and communicates frequently; pipeline parallel partitions layers and introduces bubbles; data parallel replicates weights and scales requests; expert parallel distributes MoE experts and pays all-to-all/imbalance; context parallel partitions long contexts. Choose from model fit, topology, batch, sequence length, and failure domain—not device count alone.

## Q8. Execution shapes
[Philosophy](level-1-philosophy.md#q8-when-should-repeated-gpu-work-be-recorded-and-replayed) · [Lab](level-3-code-labs.md#q8-shape-cache)

CUDA graphs capture selected batch/token shapes and replay without Python/driver launch work. Inputs occupy stable buffers; requests may be padded to captured sizes; unsupported dynamic paths use eager execution. Follow-ups: warmup, graph-memory overhead, padding waste, invalidation after model changes, and why many rare shapes should not all be captured.

## Q9. Engine ownership
[Philosophy](level-1-philosophy.md#q9-who-owns-request-lifecycle-versus-device-execution) · [Lab](level-3-code-labs.md#q9-fenced-worker)

Front-end code validates/tokenizes; EngineCore owns request state, scheduler, and KV manager; executors coordinate workers; model runners perform device work; output processors detokenize and stream. Cancellation returns to the owner, which frees resources once. Follow-ups: process isolation, worker death, stale completion fencing, and control-plane versus data-plane scaling. Source: [`vllm/v1/engine`](https://github.com/vllm-project/vllm/tree/5df63a7203cdb9328d824a27b682e77c7b9928be/vllm/v1/engine).

## Q10. Streaming and cancellation
[Philosophy](level-1-philosophy.md#q10-how-do-streaming-and-cancellation-stay-bounded) · [Lab](level-3-code-labs.md#q10-bounded-stream)

Incremental token IDs flow through output processing and detokenization to bounded consumer paths. Abort must be idempotent across queued/running/finished races and release KV, encoder, structured-output, and speculative state. Observe TTFT, ITL, end-to-end latency, queued/running counts, KV usage, prefix hit rate, preemptions, and output backlog.

