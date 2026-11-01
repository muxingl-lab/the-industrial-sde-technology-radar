# Online Repartitioning

[Comparisons](README.md) · [Redis slot migration](../../redis/level-1-philosophy.md#q12-how-do-you-repartition-a-live-keyspace) · [Valkey atomic slot-range migration](../../valkey/level-1-philosophy.md#q4-how-can-ownership-of-many-live-partitions-move-as-one-atomic-operation)

## Common problem

A live keyspace must move between owners without stopping unrelated traffic. Clients can hold stale routes, writes continue during copying, and any ambiguity about authority can lose or duplicate acknowledged effects.

## Different movement units and protocols

Redis exposes stable hash slots and explicit importing/migrating states. An operator or orchestration layer moves keys and clients follow temporary `ASK` versus permanent `MOVED` redirections. The stable slot is the indirection unit, but completion across many slots remains an orchestration concern.

Valkey's atomic slot migration makes a named range migration a server-side replication-and-failover job. It snapshots the selected slots, streams concurrent mutations, bounds final lag, briefly pauses writes, and changes ownership for the range together.

This difference is fundamental rather than cosmetic. The Redis mechanism optimizes flexible incremental movement and visible per-key transition. The Valkey mechanism adds a compound atomicity goal across a slot set and therefore needs a durable job identity, two-sided state machines, catch-up accounting, and a fenced handoff.

## Shared invariant

At the ownership boundary there is one write authority, every acknowledged mutation belongs to the old or new generation, and stale routing cannot silently make an old owner authoritative again.

## Selection rule

Use independently migrated stable partitions when orchestration flexibility and small movement units dominate. Use a coordinated snapshot-plus-log handoff when an application requires a related partition range to switch together. In both cases, test crashes before and after the ownership decision—not only steady-state copy throughput.
