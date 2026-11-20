# Cross-System Atomicity

[Comparisons](README.md) · [Redis atomicity boundary](../../redis/level-1-philosophy.md#q14-where-does-atomicity-actually-end) · [Feast cross-store writes](../../feast/level-1-philosophy.md#q8-what-should-happen-when-one-logical-feature-write-targets-two-stores) · [Flink external effects](../../flink/level-1-philosophy.md#q5-how-can-recovered-computation-agree-with-an-external-side-effect)

## Common problem

One logical operation produces side effects in systems that do not share a transaction. A crash or timeout can leave partial success, and the caller may not know which effects committed.

| Dimension | Redis plus external system | Feast online plus offline stores | Flink plus transactional sink |
|---|---|---|---|
| Local atomic boundary | One Redis command or transaction | One provider write, subject to backend guarantees | One completed Flink checkpoint |
| Durable intent | Transactional outbox or authoritative log | Push journal or authoritative ingestion log | Checkpointed committable or transaction handle |
| Identity | Operation/idempotency key | Feature write ID plus entity and version | Checkpoint, attempt, and external transaction ID |
| Repair | Retry consumer and reconcile external state | Retry missing destination and compare feature versions | Recover pending transactions and commit idempotently |
| Success claim | Local commit is not external completion | SDK completion is not a cross-store transaction | Checkpoint exactly-once needs sink participation |

## Why the difference matters

The recovery pattern is shared: persist intent, make destinations idempotent, expose partial progress, and reconcile. The ordering objective differs. A business side effect may require causal order with a Redis state change; a feature write often prioritizes immediate online availability while offline state catches up. Flink has a recurring global epoch, so a transactional connector can stage a batch and use checkpoint completion as commit authority. That is a fundamental advantage only when the destination supplies a durable transaction or idempotent commit; it cannot be manufactured by the stream runtime alone.
