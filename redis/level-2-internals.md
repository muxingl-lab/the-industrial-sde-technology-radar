# Redis Source Study — Level 2: Internals and Interviews

[Radar home](../README.md) · [Redis home](README.md) · [Level 1](level-1-philosophy.md) · [Level 3](level-3-code-labs.md)

Level 2 is the interview-complete layer. For every question, be able to explain the workflow, preserve the invariant, discuss complexity, identify failure modes, and answer the follow-ups.

## Q1. Incremental work

[Philosophy](level-1-philosophy.md#q1-how-do-you-prevent-a-large-maintenance-operation-from-destroying-tail-latency) · [Code lab](level-3-code-labs.md#q1-incremental-hash-map) · [Redis `dict.c`](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/dict.c)

### Workflow

Redis begins a resize by allocating a second hash table. Reads consult both tables; new entries go to the new table; each rehash step moves a bounded number of buckets. Normal operations opportunistically advance rehashing, and periodic maintenance advances it when traffic is low. Once the old table is empty, Redis promotes the new table.

`dictRehash(d, n)` limits both migrated buckets and visits to empty buckets. The second limit matters because “move 10 buckets” is not bounded if finding them requires scanning millions of empty positions.

### Invariants

- Every key is reachable from exactly one of the two tables.
- New writes cannot be lost in the table being retired.
- Delete and lookup understand the two-table state.
- Iteration either pauses rehashing or explicitly tolerates movement.
- A step has a bounded work or time cost.

### Interview follow-ups

**Why not stop-the-world resize?** Average complexity hides latency spikes. A server with a P99 SLO cares about the longest pause, not just amortized O(1).

**Can incremental work starve?** Yes. Reserve maintenance budget, track debt, and increase effort under sustained backlog without violating the foreground latency ceiling.

**How does SCAN survive resize?** Redis uses a stateless cursor based on bit-reversed bucket traversal. It avoids blocking and large server-side cursor state, but callers must tolerate duplicates and weak consistency.

**Where else is this used?** Schema backfills, index construction, garbage collection, compaction, cache warming, shard migration, and deletion of large directory trees.

## Q2. Adaptive representation

[Philosophy](level-1-philosophy.md#q2-when-should-one-logical-data-type-have-several-physical-representations) · [Code lab](level-3-code-labs.md#q2-adaptive-integer-set) · [Redis `t_set.c`](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/t_set.c)

### Workflow

Creation uses value type and a size hint to select an initial encoding. Integer-only small sets can use a width-specialized ordered array; small generic collections can use a compact listpack; larger collections use a hash table. Mutations test thresholds and convert when the current representation no longer satisfies type or size constraints.

### Decision model

Compare total bytes per item, locality, lookup complexity, mutation frequency, conversion cost, and worst-case operation time. A contiguous O(N) structure can beat an O(1) hash table for small N because it avoids pointers and cache misses.

### Interview follow-ups

**Should conversion be reversible?** Usually only with hysteresis and a clear benefit. Bidirectional conversion near one threshold can oscillate.

**What can go wrong during conversion?** Temporary double memory, latency spikes, pointer invalidation, iterator invalidation, and incomplete rollback after allocation failure.

**How do you select thresholds?** Measure representative distributions and hardware; include allocator overhead and P99 mutation latency, not just serialized size.

**Related patterns?** Java small-string optimization analogues, database dictionary encoding, sparse/dense vectors, and inline storage in C++ containers.

## Q3. Multiple access paths

[Philosophy](level-1-philosophy.md#q3-what-should-you-do-when-one-data-set-must-support-incompatible-access-patterns) · [Code lab](level-3-code-labs.md#q3-dual-index-ranked-set) · [Redis `t_zset.c`](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/t_zset.c)

### Workflow

A large Redis Sorted Set keeps a dictionary from member to score/node and a skip list ordered by `(score, member)`. Lookup uses the dictionary. Range, rank, and ordered traversal use the skip list. Both reference the same member storage where possible to avoid duplicate payload ownership.

### Invariants

- Both indexes describe the same member set.
- A score update changes the ordered index consistently.
- Ownership rules prevent double-free and dangling pointers.
- Tie-breaking is deterministic.

### Interview follow-ups

**Why a skip list?** Expected O(log N) mutation, natural range iteration, comparatively simple implementation, spans for rank, and a level-0 back pointer for reverse traversal. “It is faster than a tree” is not a sufficient answer.

**What is the database analogue?** A primary record plus secondary indexes/materialized views. Every extra read path creates write amplification and repair requirements.

**How do you recover from divergence?** Choose one source of truth, validate counts/checksums, rebuild the derived index, and make repair observable.

## Q4. Approximation

[Philosophy](level-1-philosophy.md#q4-when-is-an-approximate-answer-the-correct-engineering-answer) · [Code lab](level-3-code-labs.md#q4-sampled-eviction) · [Redis `evict.c`](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/evict.c)

### Workflow

For eviction, Redis samples keys and inserts promising victims into a small ordered pool. LRU uses approximate idle time; LFU stores a compact logarithmic counter plus decay time. For cardinality, HyperLogLog hashes values into registers and estimates the total from their distribution, using sparse and dense representations.

### Decision model

Write down: required confidence/error, cost of false positives/negatives, workload skew, adversarial inputs, merge requirements, and whether individual members must be enumerated.

### Interview follow-ups

**Why not exact LRU?** Updating a global recency list on every read creates pointer writes, metadata overhead, and contention. Sampling trades a small hit-rate loss for cheaper access.

**Why logarithmic LFU increments?** A tiny counter would saturate under linear increments. Probabilistic growth expands its effective range; decay allows old popularity to fade.

**When is HyperLogLog wrong?** When exact billing/auditing is required or when callers need the members. It answers approximate cardinality, not membership.

**How do you validate approximation?** Replay production-like distributions, compare with an exact oracle, measure business loss and resource savings, and test sudden workload shifts.

## Q5. Deferred reclamation

[Philosophy](level-1-philosophy.md#q5-how-do-you-remove-a-large-object-without-making-deletion-a-long-request) · [Code lab](level-3-code-labs.md#q5-deferred-free) · [Redis `lazyfree.c`](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/lazyfree.c)

### Workflow

The owner thread removes the object from the keyspace, making it unreachable to new commands. If estimated free effort is large, it transfers the last ownership reference to a background job. The worker performs destruction without accessing live dictionary state.

### Interview follow-ups

**Why not defer every free?** Queueing and thread synchronization cost more than direct destruction for small objects. Use a work estimate or threshold.

**What new failure mode appears?** Reclamation debt. Logical memory usage can fall while allocator memory remains high. Monitor queued objects/bytes, worker throughput, and process RSS.

**How is this different from garbage collection?** Both separate reachability from reclamation, but Redis explicitly chooses objects and transfers ownership to a specialized queue.

**What about shutdown?** Define whether shutdown drains, cancels, or abandons jobs; never free the same object from both paths.

## Q6. State ownership

[Philosophy](level-1-philosophy.md#q6-how-can-a-mostly-single-threaded-system-safely-use-background-threads) · [Code lab](level-3-code-labs.md#q6-owner-and-worker) · [Redis `bio.c`](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/bio.c)

### Workflow

The main event-loop thread owns command ordering and authoritative structures. Background jobs receive immutable data or transferred ownership. Completion is delivered through a queue/notification mechanism and applied by the owner if live state must change.

### Interview follow-ups

**What work is safe to offload?** Pure computation on immutable snapshots, destruction of detached objects, blocking syscalls with isolated descriptors, and work producing a completion message.

**What work is unsafe?** Arbitrary mutation of live dictionaries, client state, or refcounts without a complete synchronization design.

**Why can one owner outperform fine-grained locking?** It removes lock coordination and makes ordering explicit. It loses when one request performs long CPU work or the workload cannot be partitioned.

**How do I/O threads help?** They can parallelize parsing/read/write work while keeping command execution and state mutation serialized.

## Q7. Expiration

[Philosophy](level-1-philosophy.md#q7-how-should-a-system-delete-expired-data-that-nobody-reads) · [Code lab](level-3-code-labs.md#q7-hybrid-expiration) · [Redis `expire.c`](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/expire.c)

### Workflow

On access, Redis checks the deadline and treats an expired key as absent. Separately, active expiration removes unvisited stale keys. The active cycle processes a bounded number of databases/items, measures how many samples are expired, repeats when stale density is high, and stops at a time limit. Newer expiration buckets improve deadline-oriented collection.

### Interview follow-ups

**Why not one timer per key?** Timer objects and priority-queue maintenance can be expensive at huge cardinality; simultaneous deadlines create bursts.

**Why not scan the whole keyspace?** It violates latency and CPU budgets.

**What does TTL guarantee?** Visibility after the deadline, subject to command semantics; physical memory reclamation can lag.

**How do you handle clock changes?** Prefer monotonic time for elapsed-time budgets and carefully define wall-clock semantics for absolute deadlines.

## Q8. Copy-on-write snapshot

[Philosophy](level-1-philosophy.md#q8-how-can-an-in-memory-service-create-a-consistent-snapshot-while-continuing-to-serve-writes) · [Code lab](level-3-code-labs.md#q8-snapshot-state-machine) · [Redis `rdb.c`](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/rdb.c)

### Workflow

The parent forks. The child sees the address space at the fork boundary and serializes it. Parent writes continue; modified pages become private through COW. The child writes a temporary file, validates completion, and the parent atomically installs the result.

### Interview follow-ups

**What determines COW overhead?** Dataset size, dirty-page rate, allocator layout, huge pages, child duration, and whether small logical writes dirty large pages.

**Can fork itself pause?** Yes. Creating page tables and kernel bookkeeping can produce latency proportional to memory footprint.

**Alternative designs?** MVCC/versioned objects, application-level snapshots, write barriers, or an external storage engine. Each moves complexity elsewhere.

**What should be monitored?** Fork duration, COW bytes, child duration, RSS peak, page faults, disk latency, and save failures.

## Q9. Log compaction

[Philosophy](level-1-philosophy.md#q9-how-do-you-keep-an-append-only-history-from-growing-forever) · [Code lab](level-3-code-labs.md#q9-log-rewrite) · [Redis `aof.c`](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/aof.c)

### Workflow

Create a compact representation of current state in a temporary file. Track writes that occur after the snapshot/rewrite boundary. Ensure the replacement includes a valid boundary plus the concurrent tail. Flush according to the durability policy, then atomically update the manifest or rename files.

### Interview follow-ups

**What can crash at each phase?** Before temp creation, during write, after fsync, during rename, and after manifest update. Recovery must select only a complete, validated generation.

**Why not edit the log in place?** A crash can destroy both old and new state. Immutable generations plus atomic pointer/manifest replacement give a recoverable boundary.

**How does this relate to LSM trees?** Both transform append-friendly history into compact state while foreground writes continue; both face write amplification and scheduling problems.

## Q10. Incremental recovery

[Philosophy](level-1-philosophy.md#q10-how-should-a-replica-recover-after-a-short-disconnection) · [Code lab](level-3-code-labs.md#q10-bounded-replay-log) · [Redis `replication.c`](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/replication.c)

### Workflow

The primary assigns a replication identity and monotonically advances an offset as it emits replication bytes. A bounded backlog retains a suffix. A reconnecting replica presents identity and desired offset. If both match retained history, the primary locates and streams the suffix; otherwise it sends a full snapshot and establishes a new continuation point.

### Interview follow-ups

**Why identity plus offset?** Offset 100 from a different history is unrelated. Identity/epoch prevents replay from the wrong leader lineage.

**How large should backlog be?** Start with peak replication byte rate × target disconnection window, add safety margin, then validate against memory budget and observed full-resync frequency.

**Why blocks plus an index?** Blocks make append, sharing, and incremental trimming cheaper; a sparse index avoids walking from the beginning to find an offset.

**What must the consumer do?** Apply replay idempotently or exactly at the expected position, persist progress safely, and detect gaps.

## Q11. Backpressure

[Philosophy](level-1-philosophy.md#q11-what-should-happen-when-a-consumer-is-slower-than-a-producer) · [Code lab](level-3-code-labs.md#q11-bounded-output-buffer) · [Redis `networking.c`](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/networking.c)

### Workflow

Replies first accumulate in per-client buffers and are flushed when sockets are writable. Redis accounts for logical and allocator memory, uses different policies by client type, and disconnects clients that exceed hard limits or remain over soft limits long enough.

### Interview follow-ups

**Why soft and hard limits?** A brief burst may be harmless; sustained growth is not. A hard limit prevents immediate catastrophe, while a soft limit tolerates transient spikes.

**Which metric matters?** Queue bytes, oldest-item age, production/consumption rate, blocked duration, and total memory—not just queue length.

**What are the choices under overload?** Slow producers, reject new work, drop old/new data, degrade response size, spill to disk, or disconnect consumers. State the semantic loss of each.

## Q12. Online resharding

[Philosophy](level-1-philosophy.md#q12-how-do-you-repartition-a-live-keyspace) · [Code lab](level-3-code-labs.md#q12-slot-router) · [Redis cluster source](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/cluster_legacy.c)

### Workflow

Keys map to one of 16,384 slots; slots map to nodes. Rebalancing changes slot ownership and migrates keys. `MOVED` communicates the stable owner and can update the client cache. `ASK` is temporary during migration: send this operation to the target but do not permanently rewrite routing.

### Interview follow-ups

**Why slots instead of direct consistent hashing?** Slots provide explicit, inspectable migration units and a compact routing table. Consistent hashing reduces movement but does not remove migration coordination.

**How do multi-key operations work?** Keys generally must share a slot; hash tags let applications deliberately colocate related keys.

**What if routing is stale?** Requests receive redirects and retry with a bounded loop. Operations must tolerate retries and topology churn.

**What about a hot key?** Balanced slots do not guarantee balanced traffic. Replication, local caching, key splitting, or application redesign may be required.

## Q13. Failure suspicion

[Philosophy](level-1-philosophy.md#q13-how-should-a-distributed-system-decide-that-a-node-has-failed) · [Code lab](level-3-code-labs.md#q13-suspicion-tracker) · [Redis cluster source](https://github.com/redis/redis/blob/76ec1c311045cf2f28332a95631259cc67ad4b51/src/cluster_legacy.c)

### Workflow

A node that misses expected communication marks a peer as probably failing (`PFAIL`). Nodes gossip observations. When enough eligible masters report the condition within the validity window, the cluster promotes it to `FAIL`, enabling failover decisions.

### Interview follow-ups

**Why not trust one observer?** Its network path or process may be the faulty component. Multiple observations reduce unilateral false positives.

**Does majority make failure detection perfect?** No. It changes the decision rule; partitions, asymmetric reachability, and pauses remain possible.

**How should timeouts be chosen?** From network latency distribution, pause behavior, desired detection time, and false-positive cost—not an arbitrary small number.

**What makes failover safe?** Detection alone is insufficient. Leader election, epochs/configuration versions, quorum, and fencing of stale leaders are separate requirements.

## Q14. Atomicity boundaries

[Philosophy](level-1-philosophy.md#q14-where-does-atomicity-actually-end) · [Code lab](level-3-code-labs.md#q14-idempotent-command-handler) · [Redis transactions](https://redis.io/docs/latest/develop/using-commands/transactions/)

### Workflow

Redis serializes command execution on the owner thread. MULTI/EXEC queues and then executes a batch without interleaving normal commands; Lua/Functions can perform conditional read-modify-write locally. Redis does not provide a general rollback log for runtime errors, and local atomicity does not cover external systems.

### Interview follow-ups

**Why no traditional rollback?** Redis favors a simple execution model. Command errors generally do not corrupt internal invariants; implementing arbitrary undo would add substantial complexity and cost.

**How do you combine SQL and Redis?** Usually SQL is authoritative: commit SQL plus an Outbox record, publish via CDC, invalidate/update Redis idempotently, and tolerate a bounded stale window.

**How do idempotency keys work?** Bind a client operation ID to request identity and stored outcome under one atomic owner. Duplicate identical requests return the recorded result; conflicting reuse is rejected.

**Why might a Redis lock need fencing?** A client can pause beyond lease expiry and later resume. A monotonically increasing fencing token lets the protected resource reject stale holders; ownership tokens alone only make unlock safer.
