# Cross-System Atomicity

[Comparisons](README.md) · [Redis atomicity boundary](../../redis/level-1-philosophy.md#q14-where-does-atomicity-actually-end) · [Feast cross-store writes](../../feast/level-1-philosophy.md#q8-what-should-happen-when-one-logical-feature-write-targets-two-stores)

## Common problem

One logical operation produces side effects in systems that do not share a transaction. A crash or timeout can leave partial success, and the caller may not know which effects committed.

| Dimension | Redis plus external system | Feast online plus offline stores |
|---|---|---|
| Local atomic boundary | One Redis command or transaction | One provider write, subject to backend guarantees |
| Durable intent | Transactional outbox or authoritative log | Push journal or authoritative ingestion log |
| Identity | Operation/idempotency key | Feature write ID plus entity and version |
| Repair | Retry consumer and reconcile external state | Retry missing destination and compare feature versions |
| Success claim | Local commit is not external completion | SDK method completion must not imply cross-store transactionality |

## Why the difference matters

The recovery pattern is shared: persist intent, make destinations idempotent, expose partial progress, and reconcile. The ordering objective differs. A business side effect may require causal order with a Redis state change; a feature write often prioritizes immediate online availability while offline state catches up. The state machine must encode that policy instead of hiding it behind a dual-write helper.
