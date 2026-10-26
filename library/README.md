# Problem Library

[Radar home](../README.md) · [Comparisons](comparisons/README.md) · [Pattern schema](schema.md) · [Contributing](../CONTRIBUTING.md)

Each row is one implementation of one problem in one service. Similar rows remain separate because the service-specific constraints matter. The comparison column connects implementations that belong to the same broader pattern.

Overlap is many-to-many. A question can participate in several patterns, and every pattern can include any number of services. [`patterns.json`](patterns.json) is the canonical membership registry; comparison chapters are N-way views, never an expanding matrix of service pairs.

## Memory and representation

| Service | Problem | Primary pattern | Comparison |
|---|---|---|---|
| Redis | [Choose physical representations as collections change](../redis/level-1-philosophy.md#q2-when-should-one-logical-data-type-have-several-physical-representations) | Adaptive encoding | — |
| Redis | [Support incompatible access patterns](../redis/level-1-philosophy.md#q3-what-should-you-do-when-one-data-set-must-support-incompatible-access-patterns) | Multiple indexes | — |
| Redis | [Reclaim large objects without blocking requests](../redis/level-1-philosophy.md#q5-how-do-you-remove-a-large-object-without-making-deletion-a-long-request) | Deferred reclamation | [Ownership and deferred work](comparisons/ownership-and-background-work.md) |
| vLLM | [Grow per-request state without maximum reservation](../vllm/level-1-philosophy.md#q1-how-can-per-request-memory-grow-without-reserving-its-maximum-size) | Paged allocation | [Memory indirection](comparisons/memory-indirection.md) |
| vLLM | [Handle demand beyond accelerator capacity](../vllm/level-1-philosophy.md#q5-what-happens-when-active-requests-need-more-accelerator-memory-than-exists) | Admission and preemption | [Overload and backpressure](comparisons/overload-and-backpressure.md) |
| SGLang | [Map logical token positions to physical slots](../sglang/level-1-philosophy.md#q9-how-should-logical-token-positions-map-to-reusable-physical-memory-slots) | Pool indirection | [Memory indirection](comparisons/memory-indirection.md) |
| SGLang | [Place reusable state across memory tiers](../sglang/level-1-philosophy.md#q4-how-should-reusable-model-state-move-across-gpu-host-memory-and-storage) | Hierarchical caching | — |

## Scheduling and latency

| Service | Problem | Primary pattern | Comparison |
|---|---|---|---|
| Redis | [Bound pauses from large maintenance work](../redis/level-1-philosophy.md#q1-how-do-you-prevent-a-large-maintenance-operation-from-destroying-tail-latency) | Incremental work | [Bounded work](comparisons/bounded-work.md) |
| Redis | [Run background work without corrupting owner state](../redis/level-1-philosophy.md#q6-how-can-a-mostly-single-threaded-system-safely-use-background-threads) | Single owner and handoff | [Ownership and deferred work](comparisons/ownership-and-background-work.md) |
| Redis | [Remove expired data without full scans](../redis/level-1-philosophy.md#q7-how-should-a-system-delete-expired-data-that-nobody-reads) | Passive plus budgeted active cleanup | [Bounded work](comparisons/bounded-work.md) |
| vLLM | [Continuously batch asynchronous requests](../vllm/level-1-philosophy.md#q2-how-do-asynchronous-requests-share-the-gpu-efficiently) | Iteration scheduling | [Continuous batching](comparisons/continuous-batching.md) |
| vLLM | [Mix long inputs with one-step generation](../vllm/level-1-philosophy.md#q3-how-can-long-inputs-coexist-with-requests-that-need-one-quick-step) | Chunked work | [Bounded work](comparisons/bounded-work.md) |
| vLLM | [Separate lifecycle ownership from device execution](../vllm/level-1-philosophy.md#q9-who-owns-request-lifecycle-versus-device-execution) | Owner and workers | [Ownership and deferred work](comparisons/ownership-and-background-work.md) |
| SGLang | [Continuously batch asynchronous requests](../sglang/level-1-philosophy.md#q2-how-are-asynchronous-requests-continuously-batched) | Request-state scheduling | [Continuous batching](comparisons/continuous-batching.md) |
| SGLang | [Mix long inputs with active output streams](../sglang/level-1-philosophy.md#q3-how-can-long-inputs-share-the-gpu-with-active-output-streams) | Dynamic chunking | [Bounded work](comparisons/bounded-work.md) |
| SGLang | [Preserve ownership across a serving pipeline](../sglang/level-1-philosophy.md#q10-how-does-a-multi-process-serving-pipeline-preserve-ownership) | Fenced staged pipeline | [Ownership and deferred work](comparisons/ownership-and-background-work.md); [overload and backpressure](comparisons/overload-and-backpressure.md) |

## Reuse, approximation, and speculation

| Service | Problem | Primary pattern | Comparison |
|---|---|---|---|
| Redis | [Choose when approximate answers are acceptable](../redis/level-1-philosophy.md#q4-when-is-an-approximate-answer-the-correct-engineering-answer) | Sampling and sketches | — |
| vLLM | [Reuse shared-prefix computation safely](../vllm/level-1-philosophy.md#q4-when-is-prefix-computation-safely-reusable) | Content-addressed blocks | [Prefix reuse](comparisons/prefix-reuse.md) |
| vLLM | [Verify cheap multi-token predictions](../vllm/level-1-philosophy.md#q6-how-can-cheap-predictions-reduce-calls-to-an-expensive-model) | Speculate and verify | [Speculative execution](comparisons/speculative-execution.md) |
| SGLang | [Find the longest shared request prefix](../sglang/level-1-philosophy.md#q1-how-can-the-server-find-the-longest-shared-beginning-between-requests) | Radix-tree reuse | [Prefix reuse](comparisons/prefix-reuse.md) |
| SGLang | [Adapt how far a cheap predictor runs ahead](../sglang/level-1-philosophy.md#q7-how-far-ahead-should-a-cheaper-predictor-be-allowed-to-work) | Feedback-controlled speculation | [Speculative execution](comparisons/speculative-execution.md) |

## Persistence, replication, and distribution

| Service | Problem | Primary pattern | Comparison |
|---|---|---|---|
| Redis | [Create a consistent snapshot while serving writes](../redis/level-1-philosophy.md#q8-how-can-an-in-memory-service-create-a-consistent-snapshot-while-continuing-to-serve-writes) | Copy-on-write snapshot | — |
| Redis | [Compact append-only history](../redis/level-1-philosophy.md#q9-how-do-you-keep-an-append-only-history-from-growing-forever) | Rewrite and atomic generation switch | — |
| Redis | [Resume a replica after disconnection](../redis/level-1-philosophy.md#q10-how-should-a-replica-recover-after-a-short-disconnection) | Identity, offset, bounded history | — |
| Redis | [Repartition a live keyspace](../redis/level-1-philosophy.md#q12-how-do-you-repartition-a-live-keyspace) | Stable slots and migration states | — |
| Redis | [Turn failure suspicion into a cluster decision](../redis/level-1-philosophy.md#q13-how-should-a-distributed-system-decide-that-a-node-has-failed) | Gossip, quorum, fencing | — |
| Redis | [Define the true atomicity boundary](../redis/level-1-philosophy.md#q14-where-does-atomicity-actually-end) | Idempotency and outbox | — |
| SGLang | [Transfer state between specialized worker fleets](../sglang/level-1-philosophy.md#q5-when-should-input-processing-and-token-generation-use-separate-worker-fleets) | Disaggregation protocol | — |

## Execution, parallelism, and output

| Service | Problem | Primary pattern | Comparison |
|---|---|---|---|
| Redis | [Bound memory from slow consumers](../redis/level-1-philosophy.md#q11-what-should-happen-when-a-consumer-is-slower-than-a-producer) | Soft/hard output limits | [Overload and backpressure](comparisons/overload-and-backpressure.md) |
| vLLM | [Choose a model-parallelism dimension](../vllm/level-1-philosophy.md#q7-which-parallelism-dimension-should-scale-the-model) | TP/PP/DP/EP decomposition | — |
| vLLM | [Capture and replay repeated GPU work](../vllm/level-1-philosophy.md#q8-when-should-repeated-gpu-work-be-recorded-and-replayed) | Stable execution shapes | — |
| vLLM | [Bound streaming and cancellation](../vllm/level-1-philosophy.md#q10-how-do-streaming-and-cancellation-stay-bounded) | Bounded queues and propagated abort | [Overload and backpressure](comparisons/overload-and-backpressure.md) |
| SGLang | [Constrain output to a grammar](../sglang/level-1-philosophy.md#q6-how-is-schema-conforming-output-guaranteed) | Grammar-state token masking | — |
| SGLang | [Route by load and cached state](../sglang/level-1-philosophy.md#q8-how-should-replicas-be-selected-when-both-load-and-cache-locality-matter) | Locality-aware routing | — |
