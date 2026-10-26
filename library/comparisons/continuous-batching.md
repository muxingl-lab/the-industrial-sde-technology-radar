# Continuous Batching Across Serving Engines

[Comparisons](README.md) · [vLLM question](../../vllm/level-1-philosophy.md#q2-how-do-asynchronous-requests-share-the-gpu-efficiently) · [SGLang question](../../sglang/level-1-philosophy.md#q2-how-are-asynchronous-requests-continuously-batched)

## Common problem

Static batches lose capacity as requests finish. Both engines rebuild executable work at iteration boundaries and admit new requests without waiting for the old batch to drain.

## Shared invariant

A request has one authoritative lifecycle. Scheduling may change its batch membership, but it must not duplicate progress, lose reserved memory, or publish output out of order.

## Different emphasis

vLLM's V1 scheduler centers the schedule around token budgets and KV-cache allocation. SGLang's scheduler integrates request lifecycle with radix-prefix matching, memory pools, retraction, and a broader staged runtime. Both are continuous batchers; their scheduler state reflects different adjacent subsystems.

This is an operational difference, not a different core pattern. The useful comparison is not which loop has more features. It is which state the scheduler must make atomic when it admits one more token of work.

## Design test

For either engine, ask what happens when allocation succeeds but scheduling fails, cancellation arrives during execution, or a worker returns after the request has finished. Those paths reveal the real ownership model.
