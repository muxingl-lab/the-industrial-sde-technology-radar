# Ownership and Background Work

[Comparisons](README.md) · [Redis owner thread](../../redis/level-1-philosophy.md#q6-how-can-a-mostly-single-threaded-system-safely-use-background-threads) · [Redis deferred free](../../redis/level-1-philosophy.md#q5-how-do-you-remove-a-large-object-without-making-deletion-a-long-request) · [vLLM engine ownership](../../vllm/level-1-philosophy.md#q9-who-owns-request-lifecycle-versus-device-execution) · [SGLang pipeline](../../sglang/level-1-philosophy.md#q10-how-does-a-multi-process-serving-pipeline-preserve-ownership)

## Common problem

Slow or parallel work must leave the main control path, but authoritative mutable state cannot acquire several independent owners.

## Ownership boundaries

Redis detaches an object before a background thread frees it; the worker owns unreachable memory, not the live keyspace. vLLM keeps request scheduling and cache lifecycle in the engine core while workers execute a plan. SGLang spreads work across pipeline stages and uses request identity and generation to reject stale messages.

These differences are fundamental because the transferred object differs. Redis can transfer final ownership of detached memory. An inference worker receives temporary execution authority but does not become the owner of request lifecycle. A staged pipeline transfers messages while lifecycle authority remains coordinated across stages.

## Review rule

For every asynchronous boundary, name the state owner before dispatch, during execution, after cancellation, and after completion. If two answers overlap, the design needs a fence, a transfer protocol, or a simpler ownership model.

