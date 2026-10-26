# Redis Source Study — Level 1: Philosophy

[Radar home](../README.md) · [Redis home](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

Level 1 answers one question: **when I see this shape of problem, what standard family of solutions should enter my mind?**

## Q1. How do you prevent a large maintenance operation from destroying tail latency?
**Starting point.** An in-memory service periodically needs to resize tables, delete expired records, compact memory, or migrate data. The work may touch millions of entries.

**What breaks.** Running the operation in one call blocks unrelated requests. Avoiding maintenance only delays the work until memory or performance becomes unacceptable.

**The question.** How can the service complete the same total work while placing a strict limit on any single pause?


**Philosophy:** Total work and maximum pause are different quantities. If O(N) work is unavoidable, turn it into resumable O(1)-sized steps governed by a time or work budget.

**Think of:** incremental rehashing, cursor-based backfills, incremental GC, online index building, partition migration.

**Redis example:** dictionary rehashing, active expiration, active defragmentation, and replication-backlog trimming.

**Warning:** incremental work creates intermediate states; every read, write, scan, and recovery path must understand them.

[Go deeper: workflow and follow-ups](level-2-internals.md#q1-incremental-work) · [Implement it](level-3-code-labs.md#q1-incremental-hash-map)

## Q2. When should one logical data type have several physical representations?
**Starting point.** A collection with five small integers and a collection with five million arbitrary strings need the same public operations. They do not have the same efficient memory layout.

**What breaks.** A universal hash-table representation adds pointers, buckets, and allocator metadata to every tiny collection. A compact array saves memory but becomes expensive as the collection grows or changes type.

**The question.** When should one logical type change its physical representation, and how can conversion avoid latency spikes and oscillation?


**Philosophy:** Big-O is not the whole cost model. For small values, pointers, allocator metadata, and cache misses can cost more than the payload. Match representation to observed distribution and upgrade at explicit thresholds.

**Think of:** small-object optimization, sparse/dense formats, column encodings, tagged unions, tiered storage.

**Redis example:** integer sets, listpacks, hash tables, and multiple encodings for Set, Hash, and Sorted Set.

**Warning:** conversion is itself an operation with latency, peak-memory, and compatibility costs.

[Go deeper](level-2-internals.md#q2-adaptive-representation) · [Implement it](level-3-code-labs.md#q2-adaptive-integer-set)

## Q3. What should you do when one data set must support incompatible access patterns?
**Starting point.** The same records may need fast lookup by identity and ordered range or rank queries. A hash table serves the first access pattern; an ordered structure serves the second.

**What breaks.** Choosing one structure makes the other query expensive. Maintaining both speeds reads but doubles update paths and creates the possibility that the indexes disagree.

**The question.** When is a second access path worth its write cost, and which invariants keep both views synchronized?


**Philosophy:** There is rarely one structure optimal for lookup, rank, range, prefix, and aggregation. Maintain multiple access paths when the read benefit justifies write amplification.

**Think of:** secondary indexes, materialized views, CQRS read models, inverted indexes.

**Redis example:** a Sorted Set combines a hash table for member lookup with a skip list for ordering and rank.

**Warning:** two structures create one correctness obligation: updates must preserve cross-index consistency.

[Go deeper](level-2-internals.md#q3-multiple-access-paths) · [Implement it](level-3-code-labs.md#q3-dual-index-ranked-set)

## Q4. When is an approximate answer the correct engineering answer?
**Starting point.** Exact recency, frequency, or distinct-count tracking often requires metadata or work proportional to the data set. Some products only need a bounded estimate.

**What breaks.** Exact tracking can consume more memory and CPU than the data path can afford. Approximation without an explicit error budget can make incorrect business decisions.

**The question.** What error can the caller tolerate, what loss does an error cause, and how much resource cost does approximation remove?


**Philosophy:** Precision is a resource. If the business can state an acceptable error, approximation may buy bounded memory, lower write amplification, and predictable latency.

**Think of:** sampling, sketches, probabilistic counters, Bloom filters, approximate eviction.

**Redis example:** sampled LRU/LFU eviction and HyperLogLog cardinality estimation.

**Warning:** never choose approximation before defining the loss function and adversarial distributions.

[Go deeper](level-2-internals.md#q4-approximation) · [Implement it](level-3-code-labs.md#q4-sampled-eviction)

## Q5. How do you remove a large object without making deletion a long request?
**Starting point.** Deleting a key from an index can be constant time, but destroying the large collection stored behind that key may require millions of frees.

**What breaks.** Performing every free on the request thread creates a long latency spike. Delaying all reclamation allows unreachable memory to accumulate.

**The question.** How can logical deletion happen immediately while physical reclamation remains bounded and observable?


**Philosophy:** Logical visibility and physical reclamation do not have to occur together. Remove the object from the authoritative index, then reclaim unreachable memory asynchronously.

**Think of:** tombstones, epoch reclamation, asynchronous compaction, deferred destruction.

**Redis example:** `UNLINK`, lazy freeing, and background I/O workers.

**Warning:** deferred reclamation improves latency but increases temporary memory usage and operational lag.

[Go deeper](level-2-internals.md#q5-deferred-reclamation) · [Implement it](level-3-code-labs.md#q5-deferred-free)

## Q6. How can a mostly single-threaded system safely use background threads?
**Starting point.** A single event-loop thread gives commands a simple execution order and avoids locks around core state. Some operations, such as file synchronization or freeing detached memory, can still block that thread.

**What breaks.** Moving arbitrary work to background threads introduces races in the state that the event loop previously owned. Keeping every slow operation on the owner thread damages latency.

**The question.** Which work can cross the thread boundary, who owns its inputs, and how does completion return without creating shared mutable state?


**Philosophy:** Separate state ownership from work execution. Keep authoritative mutation on one owner; offload only work whose inputs and completion protocol have explicit boundaries.

**Think of:** actor systems, single-writer logs, event loops, completion queues.

**Redis example:** main-thread command execution with background close, fsync, lazy free, and bounded I/O assistance.

**Warning:** adding threads without an ownership model replaces blocking with races.

[Go deeper](level-2-internals.md#q6-state-ownership) · [Implement it](level-3-code-labs.md#q6-owner-and-worker)

## Q7. How should a system delete expired data that nobody reads?
**Starting point.** Keys can carry deadlines. A read can cheaply notice that its target has expired, but many expired keys may never be read again.

**What breaks.** Scanning all deadlines continuously consumes CPU and creates pauses. Cleaning only on access leaves stale keys occupying memory indefinitely.

**The question.** How should passive checks and budgeted active cleanup work together, and what does expiration promise about visibility versus memory reclamation?


**Philosophy:** Combine cheap opportunistic cleanup with bounded proactive cleanup. Adapt effort to measured stale-data pressure instead of scanning everything continuously.

**Think of:** passive expiration, active sampling, timing wheels, deadline buckets, maintenance budgets.

**Redis example:** expire-on-access plus an active expiration cycle with an effort knob and time limit.

**Warning:** TTL normally means “not visible after the deadline,” not “memory is reclaimed at the exact deadline.”

[Go deeper](level-2-internals.md#q7-expiration) · [Implement it](level-3-code-labs.md#q7-hybrid-expiration)

## Q8. How can an in-memory service create a consistent snapshot while continuing to serve writes?
**Starting point.** An in-memory service must periodically write a recoverable image of a large, changing data set. Serializing the image may take seconds or minutes.

**What breaks.** Pausing writes for the whole save violates availability. Reading live mutable state without isolation produces a snapshot that never existed at one point in time.

**The question.** How can the service obtain a stable view quickly and serialize it outside the request path, and where does the deferred cost appear?


**Philosophy:** Obtain a stable view cheaply, then serialize it outside the request path. Copy-on-write can turn mutation after the snapshot boundary into the incremental cost.

**Think of:** fork-based snapshots, MVCC snapshots, shadow paging.

**Redis example:** background RDB save and AOF rewrite using `fork()`.

**Warning:** “background” does not mean free: fork pauses, page tables, COW memory, disk, and memory bandwidth remain shared costs.

[Go deeper](level-2-internals.md#q8-copy-on-write-snapshot) · [Implement it](level-3-code-labs.md#q8-snapshot-state-machine)

## Q9. How do you keep an append-only history from growing forever?
**Starting point.** An append-only log records every state change and supports recovery by replay. Over time, repeated updates and deletes make the file much larger than the current state.

**What breaks.** Replaying and storing the full history becomes expensive. Rewriting in place risks losing both the old and new recovery path if the process crashes.

**The question.** How can the service build a compact equivalent log while writes continue and switch generations atomically?


**Philosophy:** Periodically replace historical operations with a compact equivalent state, capture concurrent changes, then switch files atomically.

**Think of:** log compaction, checkpointing, SSTable compaction, event-log snapshots.

**Redis example:** AOF rewrite.

**Warning:** compaction creates temporary space, I/O, CPU, and coordination costs; crash safety depends on the switch protocol.

[Go deeper](level-2-internals.md#q9-log-compaction) · [Implement it](level-3-code-labs.md#q9-log-rewrite)

## Q10. How should a replica recover after a short disconnection?
**Starting point.** A replica applies an ordered stream from a primary and records how far it has progressed. Short network interruptions are normal.

**What breaks.** Rebuilding from a full snapshot after every interruption wastes network and CPU. Resuming from an offset alone is unsafe after failover because the same number may refer to different history.

**The question.** What identity, position, and retained history allow safe incremental replay, and when must the system fall back to a full snapshot?


**Philosophy:** Model synchronization as producer identity + monotonic position + bounded history. Replay when the requested position remains available; otherwise install a snapshot and resume from its boundary.

**Think of:** Kafka offsets, CDC LSNs, WAL shipping, resumable file transfer.

**Redis example:** replication ID, replication offset, backlog, PSYNC, and FULLRESYNC.

**Warning:** offsets are meaningless without producer identity or epoch; retained history is always finite.

[Go deeper](level-2-internals.md#q10-incremental-recovery) · [Implement it](level-3-code-labs.md#q10-bounded-replay-log)

## Q11. What should happen when a consumer is slower than a producer?
**Starting point.** A server can produce replies faster than a client, replica, or subscriber can read them. Pending bytes accumulate in per-client buffers.

**What breaks.** Unlimited buffering turns a slow consumer into process-wide memory exhaustion. A strict small limit disconnects clients during harmless short bursts.

**The question.** Which soft and hard bounds distinguish a temporary burst from sustained overload, and who should bear the cost when production exceeds consumption?


**Philosophy:** Queue growth must be bounded. Apply backpressure, shed load, disconnect, degrade, or spill intentionally; infinite buffering merely postpones failure until it is larger.

**Think of:** bounded queues, credits, rate limits, output-buffer policies, admission control.

**Redis example:** client output-buffer limits and special handling for replicas and Pub/Sub clients.

**Warning:** every buffering policy chooses who pays: producer latency, consumer loss, memory, disk, or availability.

[Go deeper](level-2-internals.md#q11-backpressure) · [Implement it](level-3-code-labs.md#q11-bounded-output-buffer)

## Q12. How do you repartition a live keyspace?
**Starting point.** A distributed key-value service maps keys to nodes. Adding or removing capacity requires moving ownership while clients continue sending commands.

**What breaks.** Replacing the whole mapping at once moves too much data and creates a long coordination boundary. During incremental movement, clients may hold stale routes and a key may be between source and destination.

**The question.** What stable unit of indirection supports gradual movement, and how should the protocol distinguish temporary migration from permanent ownership?


**Philosophy:** Insert stable indirection between keys and owners, expose transitional states, and make retries/re-routing idempotent.

**Think of:** virtual nodes, hash slots, shard maps, range leases, online resharding.

**Redis example:** 16,384 hash slots, slot migration, and `MOVED` versus `ASK` redirection.

**Warning:** multi-key operations, hot partitions, stale routing caches, and partial migration dominate the hard cases.

[Go deeper](level-2-internals.md#q12-online-resharding) · [Implement it](level-3-code-labs.md#q12-slot-router)

## Q13. How should a distributed system decide that a node has failed?
**Starting point.** Cluster nodes exchange heartbeats over a network that can delay or drop messages. A node that stops responding may have crashed, paused, or become unreachable only from one observer.

**What breaks.** Immediate failover on one timeout creates two active owners during transient network faults. Waiting for proof is impossible in an asynchronous network.

**The question.** How should the system turn local suspicion into a group decision, and what additional mechanism prevents a stale owner from continuing to write?


**Philosophy:** Failure detection is suspicion under uncertainty, not proof. Separate local suspicion from a group decision, and make the resulting action safe under false positives.

**Think of:** heartbeats, phi-accrual detectors, gossip, quorum confirmation, leases.

**Redis example:** local `PFAIL`, gossip propagation, and cluster `FAIL` state.

**Warning:** network partitions and long pauses are observationally similar to crashes.

[Go deeper](level-2-internals.md#q13-failure-suspicion) · [Implement it](level-3-code-labs.md#q13-suspicion-tracker)

## Q14. Where does atomicity actually end?
**Starting point.** One service may update Redis, commit a database row, publish a message, and call another service for one business operation. Each component can make its own local change atomic.

**What breaks.** The process can crash between components. Retrying may repeat a completed side effect, while rolling back one system cannot undo an external action.

**The question.** Where is the real transaction boundary, and how should operations outside it handle retries, duplicates, ordering, and compensation?


**Philosophy:** Atomic execution inside one owner does not create atomicity across databases, caches, queues, or external side effects. Mark the real transaction boundary and design everything outside it for retries.

**Think of:** idempotency keys, transactional outbox, inbox deduplication, Saga, fencing tokens.

**Redis example:** serial command execution and Lua/Functions provide local atomicity; they do not atomically commit a SQL write or an HTTP call.

**Warning:** “Redis operation is atomic” is often a true statement used to justify a false system-level conclusion.

[Go deeper](level-2-internals.md#q14-atomicity-boundaries) · [Implement it](level-3-code-labs.md#q14-idempotent-command-handler)

## Cross-system comparisons

- Q1 and Q7: [Bounded work](../library/comparisons/bounded-work.md)
- Q5 and Q6: [Ownership and background work](../library/comparisons/ownership-and-background-work.md)
- Q11: [Overload and backpressure](../library/comparisons/overload-and-backpressure.md)
