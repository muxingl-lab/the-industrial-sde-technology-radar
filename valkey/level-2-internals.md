# Valkey Source Study — Level 2: Internals and Interviews

[Radar home](../README.md) · [Valkey home](README.md) · [Level 1](level-1-philosophy.md) · [Level 3](level-3-code-labs.md)

## Q1. Adaptive I/O workers
[Philosophy](level-1-philosophy.md#q1-how-can-connection-work-run-in-parallel-without-giving-mutable-state-several-owners) · [Code lab](level-3-code-labs.md#q1-owner-thread-with-adaptive-io-workers) · [Source](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/src/io_threads.c)

The main thread owns command execution and authoritative server state. It submits accept, poll, read, write, argument-free, and object-free jobs through a shared SPMC inbox or thread-specific SPSC queues. Workers return completions through an MPSC outbox. Per-client read/write states prevent simultaneous conflicting work, while acquire/release fences make job completion visible before the main thread resumes use.

Worker activation is adaptive. With only the main thread active, Valkey samples main-thread active time and ignites a worker above a threshold. Once active, it samples queue depth, adds workers when debt persists, and removes them after an idle cooldown. This is a control loop, not a correctness rule; queue and client-state invariants must hold at every worker count.

**Invariants:** one authoritative command executor; at most one incompatible I/O job per client; every submitted job produces one completion or a terminal close path; shutdown drains queues before shared state is destroyed.

**Failure and observability:** inspect pending reads/writes, submitted versus finished jobs, queue wait, active worker count, per-thread active time, and main-thread utilization. Full queues require a bounded fallback path; thread activation that oscillates needs hysteresis.

**Interview follow-ups.** Why not execute commands on I/O threads? It would move contention into the keyspace and weaken deterministic command ordering. Why private queues? Some work must return to the thread that owns transport-local state. Why not keep all workers awake? Low-load contention and CPU cost can exceed parallelism gains.

## Q2. Staged software prefetch
[Philosophy](level-1-philosophy.md#q2-when-can-batching-independent-requests-hide-memory-latency) · [Code lab](level-3-code-labs.md#q2-staged-prefetch-batch) · [Source](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/src/memory_prefetch.c)

Valkey collects eligible clients and command keys into a bounded batch. It first prefetches command arguments, extracts key positions from command metadata, and advances each key through entry and optional value stages. The hashtable stage issues hints for several entries before consuming earlier results, creating useful independent work between pointer-dependent accesses. Commands still execute in original owner-thread order after the batch is prepared.

The batch is capped by `prefetch-batch-max-size`; unsupported, blocking, transactional, or otherwise unsafe paths must bypass batching. When reply construction avoids copies with enough I/O threads, value prefetch may be less useful, showing that optimizations interact rather than compose automatically.

**Invariants:** prefetch never changes visibility or execution order; extracted key specifications match ACL/routing semantics; removed clients leave no dangling batch entries; a configuration resize rebuilds batch storage safely.

**Measure:** prefetched entries and batches, cycles per command, LLC misses, batch fill ratio, P50/P99 queue delay, and throughput under hot-key versus random-key workloads. A throughput win with worse low-load tail latency is not universally better.

## Q3. Dual-channel full synchronization
[Philosophy](level-1-philosophy.md#q3-how-can-a-replica-receive-a-large-snapshot-without-falling-behind-on-new-writes) · [Code lab](level-3-code-labs.md#q3-snapshot-plus-change-stream) · [Source](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/src/replication.c) · [Integration tests](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/tests/integration/dual-channel-replication.tcl)

The replica advertises dual-channel capability. If partial synchronization cannot resume, the primary returns a dual-channel response. The replica opens a dedicated RDB channel while keeping the main replication channel. Before forking, the primary records the snapshot end offset and retains subsequent history. The child streams snapshot bytes directly on the RDB channel; the main channel carries post-boundary changes into a local pending buffer. After the replica loads the snapshot, it drains that buffer in offset order and enters steady state.

The pending replication buffer is explicitly accounted and checked against replica output-buffer limits. At the local hard limit, Valkey stops reading the main channel so pressure moves back to the primary's bounded replica output path instead of allocating locally without limit. Either-channel failure aborts the compound synchronization and cleans state. Producer identity and snapshot end offset are the join key; connection arrival order is not.

**Invariants:** snapshot describes one boundary; every later byte is retained once and applied in order; no mutation is visible before its snapshot base; the replica becomes connected only after both branches join; buffer memory is bounded.

**Interview follow-ups.** Why two channels? Bulk transfer no longer monopolizes the main replication/control flow or forces the parent to relay child output. Why not discard live changes and PSYNC later? Required history may fall out of the backlog. What if the local buffer hits its hard limit? Stop reading and propagate pressure to the primary; if the primary's bounded output path cannot retain the debt, synchronization fails rather than allowing unbounded memory growth.

## Q4. Atomic slot-range migration
[Philosophy](level-1-philosophy.md#q4-how-can-ownership-of-many-live-partitions-move-as-one-atomic-operation) · [Code lab](level-3-code-labs.md#q4-fenced-range-migration) · [Source](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/src/cluster_migrateslots.c) · [Tests](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/tests/unit/cluster/cluster-migrateslots.tcl)

Export and import nodes create a named migration job covering explicit slot ranges. The exporter forks a snapshot of those slots, streams it, and concurrently forwards mutations. The importer acknowledges progress. When lag is below a configured failover bound, the protocol requests a short write pause, drains remaining replication data, changes slot ownership as a group, and then resumes service. Both sides persist enough migration metadata in RDB state to recognize ongoing work after load.

The source file exposes separate import/export state machines rather than a boolean `migrating` flag. That distinction is necessary for authentication, snapshot, streaming, pause, failover grant, cleanup, cancellation, timeout, and failure paths. Job identity fences unrelated or stale messages.

**Invariants:** a slot range has one write authority at the completion boundary; snapshot plus mutation stream covers every accepted write; failover is granted only after bounded catch-up; cancellation cannot silently leave claimed ownership; retries identify the same job or create a new generation.

**Observe:** migration state and age, last acknowledgment, remaining replication bytes, COW bytes, pause duration, output-buffer debt, timeouts, and cleanup failures.

## Q5. Fine-grained expiration index
[Philosophy](level-1-philosophy.md#q5-how-should-deadlines-be-indexed-for-items-nested-inside-a-larger-object) · [Code lab](level-3-code-labs.md#q5-adaptive-deadline-index) · [Index source](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/src/vset.c) · [Expiration path](https://github.com/valkey-io/valkey/blob/29173b67508b2de4c0f0ed551f3b47cf19fc3ca8/src/expire.c)

Hash lookup remains the primary access path. Volatile fields additionally participate in a `vset`, a deadline-oriented adaptive container whose representation grows from no entry to a tagged single entry, sorted packed vector, hashtable for difficult same-deadline groups, and radix-organized deadline buckets. Buckets split as they grow. This avoids paying full ordered-index overhead for hashes with few expiring fields while still locating the earliest candidates.

Reads treat overdue fields as absent and may remove them passively. Active expiration scans databases and hashes under time and entry budgets; `dbReclaimExpiredFields` reports whether the cap was reached so maintenance can continue later. Replication and persistence paths must explicitly encode deletions or remaining deadlines because replicas cannot infer the primary's exact observation time safely.

**Invariants:** field lookup and deadline index agree for live volatile fields; changing/removing TTL updates both; active cleanup stops at its budget; expired fields are never returned even before physical removal; iteration and encoding conversion define how logically expired members behave.

**Interview follow-ups.** Why not one heap per hash? Per-node pointers and arbitrary deletion costs are high, and identical deadlines create poor shapes. Why adaptive representations? Most aggregates have zero or few volatile fields. What does TTL promise? Visibility after the deadline, not exact reclamation time.
