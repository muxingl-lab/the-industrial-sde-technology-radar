# Redis Source Study — Level 1: Philosophy

[Radar home](../README.md) · [Redis home](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

Level 1 answers one question: **when I see this shape of problem, what standard family of solutions should enter my mind?**

## Q1. How do you prevent a large maintenance operation from destroying tail latency?

**Philosophy:** Total work and maximum pause are different quantities. If O(N) work is unavoidable, turn it into resumable O(1)-sized steps governed by a time or work budget.

**Think of:** incremental rehashing, cursor-based backfills, incremental GC, online index building, partition migration.

**Redis example:** dictionary rehashing, active expiration, active defragmentation, and replication-backlog trimming.

**Warning:** incremental work creates intermediate states; every read, write, scan, and recovery path must understand them.

[Go deeper: workflow and follow-ups](level-2-internals.md#q1-incremental-work) · [Implement it](level-3-code-labs.md#q1-incremental-hash-map)

## Q2. When should one logical data type have several physical representations?

**Philosophy:** Big-O is not the whole cost model. For small values, pointers, allocator metadata, and cache misses can cost more than the payload. Match representation to observed distribution and upgrade at explicit thresholds.

**Think of:** small-object optimization, sparse/dense formats, column encodings, tagged unions, tiered storage.

**Redis example:** integer sets, listpacks, hash tables, and multiple encodings for Set, Hash, and Sorted Set.

**Warning:** conversion is itself an operation with latency, peak-memory, and compatibility costs.

[Go deeper](level-2-internals.md#q2-adaptive-representation) · [Implement it](level-3-code-labs.md#q2-adaptive-integer-set)

## Q3. What should you do when one data set must support incompatible access patterns?

**Philosophy:** There is rarely one structure optimal for lookup, rank, range, prefix, and aggregation. Maintain multiple access paths when the read benefit justifies write amplification.

**Think of:** secondary indexes, materialized views, CQRS read models, inverted indexes.

**Redis example:** a Sorted Set combines a hash table for member lookup with a skip list for ordering and rank.

**Warning:** two structures create one correctness obligation: updates must preserve cross-index consistency.

[Go deeper](level-2-internals.md#q3-multiple-access-paths) · [Implement it](level-3-code-labs.md#q3-dual-index-ranked-set)

## Q4. When is an approximate answer the correct engineering answer?

**Philosophy:** Precision is a resource. If the business can state an acceptable error, approximation may buy bounded memory, lower write amplification, and predictable latency.

**Think of:** sampling, sketches, probabilistic counters, Bloom filters, approximate eviction.

**Redis example:** sampled LRU/LFU eviction and HyperLogLog cardinality estimation.

**Warning:** never choose approximation before defining the loss function and adversarial distributions.

[Go deeper](level-2-internals.md#q4-approximation) · [Implement it](level-3-code-labs.md#q4-sampled-eviction)

## Q5. How do you remove a large object without making deletion a long request?

**Philosophy:** Logical visibility and physical reclamation do not have to occur together. Remove the object from the authoritative index, then reclaim unreachable memory asynchronously.

**Think of:** tombstones, epoch reclamation, asynchronous compaction, deferred destruction.

**Redis example:** `UNLINK`, lazy freeing, and background I/O workers.

**Warning:** deferred reclamation improves latency but increases temporary memory usage and operational lag.

[Go deeper](level-2-internals.md#q5-deferred-reclamation) · [Implement it](level-3-code-labs.md#q5-deferred-free)

## Q6. How can a mostly single-threaded system safely use background threads?

**Philosophy:** Separate state ownership from work execution. Keep authoritative mutation on one owner; offload only work whose inputs and completion protocol have explicit boundaries.

**Think of:** actor systems, single-writer logs, event loops, completion queues.

**Redis example:** main-thread command execution with background close, fsync, lazy free, and bounded I/O assistance.

**Warning:** adding threads without an ownership model replaces blocking with races.

[Go deeper](level-2-internals.md#q6-state-ownership) · [Implement it](level-3-code-labs.md#q6-owner-and-worker)

## Q7. How should a system delete expired data that nobody reads?

**Philosophy:** Combine cheap opportunistic cleanup with bounded proactive cleanup. Adapt effort to measured stale-data pressure instead of scanning everything continuously.

**Think of:** passive expiration, active sampling, timing wheels, deadline buckets, maintenance budgets.

**Redis example:** expire-on-access plus an active expiration cycle with an effort knob and time limit.

**Warning:** TTL normally means “not visible after the deadline,” not “memory is reclaimed at the exact deadline.”

[Go deeper](level-2-internals.md#q7-expiration) · [Implement it](level-3-code-labs.md#q7-hybrid-expiration)

## Q8. How can an in-memory service create a consistent snapshot while continuing to serve writes?

**Philosophy:** Obtain a stable view cheaply, then serialize it outside the request path. Copy-on-write can turn mutation after the snapshot boundary into the incremental cost.

**Think of:** fork-based snapshots, MVCC snapshots, shadow paging.

**Redis example:** background RDB save and AOF rewrite using `fork()`.

**Warning:** “background” does not mean free: fork pauses, page tables, COW memory, disk, and memory bandwidth remain shared costs.

[Go deeper](level-2-internals.md#q8-copy-on-write-snapshot) · [Implement it](level-3-code-labs.md#q8-snapshot-state-machine)

## Q9. How do you keep an append-only history from growing forever?

**Philosophy:** Periodically replace historical operations with a compact equivalent state, capture concurrent changes, then switch files atomically.

**Think of:** log compaction, checkpointing, SSTable compaction, event-log snapshots.

**Redis example:** AOF rewrite.

**Warning:** compaction creates temporary space, I/O, CPU, and coordination costs; crash safety depends on the switch protocol.

[Go deeper](level-2-internals.md#q9-log-compaction) · [Implement it](level-3-code-labs.md#q9-log-rewrite)

## Q10. How should a replica recover after a short disconnection?

**Philosophy:** Model synchronization as producer identity + monotonic position + bounded history. Replay when the requested position remains available; otherwise install a snapshot and resume from its boundary.

**Think of:** Kafka offsets, CDC LSNs, WAL shipping, resumable file transfer.

**Redis example:** replication ID, replication offset, backlog, PSYNC, and FULLRESYNC.

**Warning:** offsets are meaningless without producer identity or epoch; retained history is always finite.

[Go deeper](level-2-internals.md#q10-incremental-recovery) · [Implement it](level-3-code-labs.md#q10-bounded-replay-log)

## Q11. What should happen when a consumer is slower than a producer?

**Philosophy:** Queue growth must be bounded. Apply backpressure, shed load, disconnect, degrade, or spill intentionally; infinite buffering merely postpones failure until it is larger.

**Think of:** bounded queues, credits, rate limits, output-buffer policies, admission control.

**Redis example:** client output-buffer limits and special handling for replicas and Pub/Sub clients.

**Warning:** every buffering policy chooses who pays: producer latency, consumer loss, memory, disk, or availability.

[Go deeper](level-2-internals.md#q11-backpressure) · [Implement it](level-3-code-labs.md#q11-bounded-output-buffer)

## Q12. How do you repartition a live keyspace?

**Philosophy:** Insert stable indirection between keys and owners, expose transitional states, and make retries/re-routing idempotent.

**Think of:** virtual nodes, hash slots, shard maps, range leases, online resharding.

**Redis example:** 16,384 hash slots, slot migration, and `MOVED` versus `ASK` redirection.

**Warning:** multi-key operations, hot partitions, stale routing caches, and partial migration dominate the hard cases.

[Go deeper](level-2-internals.md#q12-online-resharding) · [Implement it](level-3-code-labs.md#q12-slot-router)

## Q13. How should a distributed system decide that a node has failed?

**Philosophy:** Failure detection is suspicion under uncertainty, not proof. Separate local suspicion from a group decision, and make the resulting action safe under false positives.

**Think of:** heartbeats, phi-accrual detectors, gossip, quorum confirmation, leases.

**Redis example:** local `PFAIL`, gossip propagation, and cluster `FAIL` state.

**Warning:** network partitions and long pauses are observationally similar to crashes.

[Go deeper](level-2-internals.md#q13-failure-suspicion) · [Implement it](level-3-code-labs.md#q13-suspicion-tracker)

## Q14. Where does atomicity actually end?

**Philosophy:** Atomic execution inside one owner does not create atomicity across databases, caches, queues, or external side effects. Mark the real transaction boundary and design everything outside it for retries.

**Think of:** idempotency keys, transactional outbox, inbox deduplication, Saga, fencing tokens.

**Redis example:** serial command execution and Lua/Functions provide local atomicity; they do not atomically commit a SQL write or an HTTP call.

**Warning:** “Redis operation is atomic” is often a true statement used to justify a false system-level conclusion.

[Go deeper](level-2-internals.md#q14-atomicity-boundaries) · [Implement it](level-3-code-labs.md#q14-idempotent-command-handler)
