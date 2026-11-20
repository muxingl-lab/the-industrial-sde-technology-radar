# Ownership and Background Work

[Comparisons](README.md) · [Redis owner thread](../../redis/level-1-philosophy.md#q6-how-can-a-mostly-single-threaded-system-safely-use-background-threads) · [Redis deferred free](../../redis/level-1-philosophy.md#q5-how-do-you-remove-a-large-object-without-making-deletion-a-long-request) · [Valkey I/O workers](../../valkey/level-1-philosophy.md#q1-how-can-connection-work-run-in-parallel-without-giving-mutable-state-several-owners) · [vLLM engine ownership](../../vllm/level-1-philosophy.md#q9-who-owns-request-lifecycle-versus-device-execution) · [SGLang pipeline](../../sglang/level-1-philosophy.md#q10-how-does-a-multi-process-serving-pipeline-preserve-ownership) · [Flink mailbox](../../flink/level-1-philosophy.md#q7-how-can-data-processing-and-control-work-share-a-task-without-concurrent-state-mutation)

## Common problem

Slow or parallel work must leave the main control path, but authoritative mutable state cannot acquire several independent owners.

## Ownership boundaries

Redis detaches an object before a background thread frees it; the worker owns unreachable memory, not the live keyspace. Valkey gives I/O workers temporary authority over explicitly staged client work while the main thread retains command and lifecycle authority. vLLM keeps request scheduling and cache lifecycle in the engine core while workers execute a plan. SGLang spreads work across pipeline stages and uses request identity and generation to reject stale messages. Flink confines operator mutation to the task thread and turns control or asynchronous completions into mailbox commands executed at safe boundaries.

These differences are fundamental because the transferred object differs. Redis can transfer final ownership of detached memory. An inference worker receives temporary execution authority but does not become the owner of request lifecycle. A staged pipeline transfers messages while lifecycle authority remains coordinated across stages. Flink transfers no mutable operator state at all: workers may compute or upload, but the mailbox linearizes the resulting command on the owner thread.

## Review rule

For every asynchronous boundary, name the state owner before dispatch, during execution, after cancellation, and after completion. If two answers overlap, the design needs a fence, a transfer protocol, or a simpler ownership model.
