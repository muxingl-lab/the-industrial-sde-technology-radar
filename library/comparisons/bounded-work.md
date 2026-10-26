# Bounded Work Across Event Loops and Accelerators

[Comparisons](README.md) · [Redis maintenance](../../redis/level-1-philosophy.md#q1-how-do-you-prevent-a-large-maintenance-operation-from-destroying-tail-latency) · [Redis expiration](../../redis/level-1-philosophy.md#q7-how-should-a-system-delete-expired-data-that-nobody-reads) · [vLLM chunking](../../vllm/level-1-philosophy.md#q3-how-can-long-inputs-coexist-with-requests-that-need-one-quick-step) · [SGLang chunking](../../sglang/level-1-philosophy.md#q3-how-can-long-inputs-share-the-gpu-with-active-output-streams)

## Common problem

One task can consume an entire latency window. Completing it in one turn improves that task's progress but blocks unrelated work. All three systems divide large work into resumable units and impose a per-iteration budget.

## What changes

| Dimension | Redis | vLLM | SGLang |
|---|---|---|---|
| Work unit | Hash buckets, expired keys, memory objects | Input tokens | Input tokens and memory-aware chunks |
| Scarce resource | Event-loop time | GPU token budget | GPU tokens plus pool capacity |
| Saved progress | Cursor or data-structure state | Processed-token count and cache blocks | Request state, prefix state, and pool mappings |
| Pressure signal | Time used or stale-key ratio | Active generation latency and token budget | Running batch, memory, and dynamic chunk feedback |

## Why the difference matters

The shared pattern is fundamental: bound foreground work and preserve continuation state. The implementation difference is operational. Redis budgets CPU time on one owner thread. LLM servers budget accelerator work and memory while many requests share a batch. A token count is not a stable time budget because model shape and batch composition change its cost.

The transferable lesson is to budget both a logical work unit and elapsed resource time. Also define starvation prevention; resumable work that is always postponed is still broken.
