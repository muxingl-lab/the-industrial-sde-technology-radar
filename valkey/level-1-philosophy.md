# Valkey Source Study — Level 1: Philosophy

[Radar home](../README.md) · [Valkey home](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

## Q1. How can connection work run in parallel without giving mutable state several owners?
**Starting point.** A request server accepts sockets, reads bytes, parses commands, executes mutations, builds replies, and writes bytes. A single event loop gives command execution a simple order, but at high request rates socket and protocol work can consume the same CPU that owns the database.

**What breaks.** Keeping everything on one thread leaves cores idle. Letting workers execute arbitrary commands in parallel destroys the single-owner ordering model and introduces locks around nearly every data structure. Permanently running the maximum worker count also wastes CPU and increases contention at low load.

**The question.** Which stages may move to workers, which thread remains authoritative, and how should worker count and handoff change with load without losing or duplicating a client operation?

**Philosophy:** parallelize work around the ownership boundary before parallelizing authoritative mutation. Use explicit queues, client states, completion barriers, and an adaptive worker policy. **Think of:** reactor/proactor servers, staged event-driven architecture, owner-worker systems. **Warning:** a client object cannot be read, written, closed, and recycled concurrently without a precise state machine.

[Go deeper](level-2-internals.md#q1-adaptive-io-workers) · [Implement it](level-3-code-labs.md#q1-owner-thread-with-adaptive-io-workers) · [Compare ownership](../library/comparisons/ownership-and-background-work.md)

## Q2. When can batching independent requests hide memory latency?
**Starting point.** A command may need to follow a hash-table bucket to an entry and then to a separately allocated value. Each dependent pointer may miss CPU cache, forcing the processor to wait before it can discover the next address.

**What breaks.** Processing one command from start to finish serializes these cache misses. Adding more execution threads is not automatically helpful when mutation must remain ordered, and blindly prefetching arbitrary addresses consumes bandwidth without enough useful work between request and use.

**The question.** How can the server interleave address discovery across independent commands so useful work overlaps memory fetch latency, while preserving command order and bounding batch delay?

**Philosophy:** batch independent work and advance each item through dependency stages; issue a prefetch only when enough unrelated work exists before use. **Think of:** software pipelining, vectorized execution, batched graph traversal. **Warning:** prefetch is a hardware hint, not a correctness mechanism, and poor locality or tiny batches can make it pure overhead.

[Go deeper](level-2-internals.md#q2-staged-software-prefetch) · [Implement it](level-3-code-labs.md#q2-staged-prefetch-batch)

## Q3. How can a replica receive a large snapshot without falling behind on new writes?
**Starting point.** A new replica needs a point-in-time snapshot and every mutation after that snapshot boundary. Creating, transferring, and loading the snapshot can take long enough for substantial new history to accumulate.

**What breaks.** Sending snapshot and live changes through one flow makes the main process relay bulk data and couples catch-up to snapshot transfer. Pausing writes for the whole operation is unacceptable. Buffering every concurrent mutation without a bound can exhaust memory if transfer or loading is slow.

**The question.** How should snapshot bytes and post-snapshot history travel concurrently, which offset joins them, and what happens when the catch-up buffer exceeds its budget or either channel fails?

**Philosophy:** separate bulk state transfer from ordered change capture, then join both streams at an explicit identity and offset. **Think of:** database base backup plus WAL, snapshot plus CDC, state transfer plus replicated log. **Warning:** two channels create a coordination protocol; success on either channel alone is not a valid replica state.

[Go deeper](level-2-internals.md#q3-dual-channel-full-synchronization) · [Implement it](level-3-code-labs.md#q3-snapshot-plus-change-stream) · [Compare overload](../library/comparisons/overload-and-backpressure.md)

## Q4. How can ownership of many live partitions move as one atomic operation?
**Starting point.** A sharded service must move a range of partitions while clients continue reading and writing. Moving keys one at a time exposes a long interval in which related keys have different owners.

**What breaks.** Client-side loops are slow, lose their own progress when interrupted, and cannot atomically change ownership for the full range. A snapshot alone misses writes made during copying. Switching ownership before the destination catches up loses data; switching it twice creates two authorities.

**The question.** What snapshot, mutation stream, pause boundary, job identity, and ownership transition let a partition range move together and recover safely from interruption?

**Philosophy:** treat online repartitioning as a stateful replication-and-failover protocol, not a file copy. **Think of:** shard split/merge, range relocation, live VM migration. **Warning:** the short final pause is small only when replication lag is already bounded.

[Go deeper](level-2-internals.md#q4-atomic-slot-range-migration) · [Implement it](level-3-code-labs.md#q4-fenced-range-migration) · [Compare online repartitioning](../library/comparisons/online-repartitioning.md)

## Q5. How should deadlines be indexed for items nested inside a larger object?
**Starting point.** A large aggregate can contain millions of independently expiring fields. Reads need fast lookup by field name, while cleanup needs the earliest deadlines. Most fields may have no deadline.

**What breaks.** Splitting every field into a top-level record destroys the aggregate API and adds metadata. Scanning every field wastes CPU. A heap provides ordered deadlines but makes removal and update bookkeeping expensive and can add large per-entry overhead.

**The question.** Which secondary index finds expired sub-items with bounded work, how does it adapt from one deadline to many, and how do passive reads, active cleanup, persistence, and replication agree on logical expiration?

**Philosophy:** keep the primary lookup structure and attach an adaptive deadline index only for volatile members. Clean passively on access and actively under a strict budget. **Think of:** timing wheels, deadline buckets, TTL secondary indexes. **Warning:** “logically expired” and “physically removed” remain different states that every iterator and replication path must understand.

[Go deeper](level-2-internals.md#q5-fine-grained-expiration-index) · [Implement it](level-3-code-labs.md#q5-adaptive-deadline-index) · [Compare bounded work](../library/comparisons/bounded-work.md)

## Cross-system comparisons

- Q1: [Ownership and background work](../library/comparisons/ownership-and-background-work.md)
- Q3: [Overload and backpressure](../library/comparisons/overload-and-backpressure.md)
- Q4: [Online repartitioning](../library/comparisons/online-repartitioning.md)
- Q5: [Bounded work](../library/comparisons/bounded-work.md)
