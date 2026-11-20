# Consistent Snapshots

[Comparisons](README.md) · [Redis copy-on-write snapshot](../../redis/level-1-philosophy.md#q8-how-can-an-in-memory-service-create-a-consistent-snapshot-while-continuing-to-serve-writes) · [Flink barrier snapshot](../../flink/level-1-philosophy.md#q4-how-can-a-distributed-computation-take-a-consistent-snapshot-while-records-keep-flowing)

## Common problem

A service needs a recovery image representing one logical point while mutations continue. A naïve component-by-component copy can mix states that never coexisted.

| Dimension | Redis | Flink |
|---|---|---|
| Cut marker | Process fork boundary | In-band checkpoint barriers |
| Concurrent mutation | Parent writes private copy-on-write pages | Operators process records around the barrier cut |
| In-flight state | Client/network activity is outside the RDB image | Aligned mode drains it; unaligned mode snapshots channel data |
| Main debt | Dirty-page copying and memory peak | Alignment latency or channel-state bytes |
| Recovery image | One database snapshot file | Distributed operator, source, and optional channel-state handles |

## Why the difference matters

The shared pattern is preserve the pre-cut view while the live owner advances. The mechanisms are fundamentally different. Redis exploits one machine's virtual-memory snapshot and creates a database image; Flink has no global memory boundary, so barriers establish a distributed cut through message ordering. Copy-on-write debt grows with pages dirtied after fork. Barrier debt grows with channel skew, backpressure, and in-flight data. Calling both “background snapshots” hides the resource that must be budgeted.
