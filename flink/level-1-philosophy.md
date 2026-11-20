# Apache Flink Source Study — Level 1: Philosophy

[Radar home](../README.md) · [Flink home](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

Level 1 assumes that the reader understands processes, records, queues, memory, clocks, and failures. It does not assume stream-processing vocabulary.

## Q1. How can a system make time-based decisions when records arrive out of order?

**Starting point.** Several producers create records with timestamps. Network delay, retries, partition skew, and paused producers mean creation order is not arrival order. A service still wants to publish “the count for minute 10” without waiting forever.

**What breaks.** The machine clock closes the minute too early; waiting for perfect certainty never completes. Taking the largest observed timestamp is also unsafe because one fast input says nothing about a slow input.

**The question.** What evidence lets the computation declare that event time has advanced, and how should silent inputs stop holding the whole graph back?

**Philosophy:** separate event time from processing time. Each input emits a monotonic lower bound—called a watermark—on timestamps still expected. A multi-input operator advances only to the minimum active input watermark; idleness is an explicit liveness decision.

**Warning:** a watermark is a policy-backed claim, not proof. Aggressive progress lowers latency by classifying more future arrivals as late.

[Temporal correctness comparison](../library/comparisons/temporal-correctness.md) · [Go deeper](level-2-internals.md#q1-event-time-progress) · [Implement it](level-3-code-labs.md#q1-watermark-valve)

## Q2. How should time-indexed state be bounded when late records are still possible?

**Starting point.** A keyed computation groups records into time intervals and stores partial aggregates plus timers. New keys and intervals arrive continuously.

**What breaks.** Keeping every interval forever leaks state. Deleting at the nominal end rejects delayed data that the business still considers valid. Re-emitting corrected results can surprise a sink that assumed one immutable output.

**The question.** When does a window fire, when is its state finally removed, and where do records beyond that boundary go?

**Philosophy:** define three separate contracts: result time, accepted-lateness interval, and cleanup time. Treat late-data correction as an output semantic, not just a runtime switch.

**Warning:** allowed lateness bounds event-time delay, not bytes. Skewed keys, large windows, or stalled watermarks can still exhaust state.

[Go deeper](level-2-internals.md#q2-windows-timers-and-late-data) · [Implement it](level-3-code-labs.md#q2-window-lifecycle)

## Q3. How can many workers update per-key state without a remote lookup for every record?

**Starting point.** Records with the same customer or device key must observe one ordered state history. The job also needs parallel workers and future rescaling.

**What breaks.** Random routing creates concurrent owners. A central database preserves ownership but adds a network round trip and a new bottleneck to every record. Hashing directly to a worker makes every parallelism change move almost every key with no stable restoration unit.

**The question.** What stable partition lies between keys and current workers, and who owns it at any moment?

**Philosophy:** hash each key into a fixed key group, assign contiguous key-group ranges to subtasks, and keep active keyed state local to its sole owner.

**Warning:** stable partitioning preserves correctness, not balance; one hot key is still indivisible without changing application semantics.

[Go deeper](level-2-internals.md#q3-keyed-state-ownership) · [Implement it](level-3-code-labs.md#q3-key-group-assignment)

## Q4. How can a distributed computation take a consistent snapshot while records keep flowing?

**Starting point.** Many operators process different records concurrently. A recovery image must contain states and input positions that could have coexisted, even though there is no shared memory or instantaneous global pause.

**What breaks.** Independently copying each worker can record an output-side effect without the upstream state that caused it, or record a record both in a channel and in downstream state. Stopping the whole graph creates unacceptable pauses.

**The question.** How can an in-band boundary cut every input consistently, and what changes when one slow input makes alignment expensive?

**Philosophy:** inject checkpoint barriers into sources and snapshot each operator at the logical cut. Aligned checkpoints hold post-barrier records until all inputs reach the cut; unaligned checkpoints include in-flight channel data instead of waiting.

**Warning:** unaligned checkpoints reduce alignment delay by moving work into snapshot size and recovery; they do not remove network congestion.

[Consistent snapshots comparison](../library/comparisons/consistent-snapshots.md) · [Go deeper](level-2-internals.md#q4-distributed-snapshots) · [Implement it](level-3-code-labs.md#q4-barrier-snapshot)

## Q5. How can recovered computation agree with an external side effect?

**Starting point.** A checkpoint can restore internal state and source positions. A record may also charge a payment, publish to a broker, or write a database that the checkpoint cannot roll back.

**What breaks.** Crash after the external write but before recorded progress causes a duplicate. Recording progress first can lose the write. “Exactly once” inside the runtime does not cross the external system boundary by itself.

**The question.** What durable intent connects the checkpoint epoch to an idempotent or transactional external commit?

**Philosophy:** stage effects under a checkpoint-scoped identity, persist that pending state with the checkpoint, and make completion the authority to commit. When transactions are unavailable, use idempotency keys and reconciliation.

**Warning:** connector claims are bounded by the sink's transaction lifetime, fencing, and recovery behavior.

[Cross-system atomicity comparison](../library/comparisons/cross-system-atomicity.md) · [Go deeper](level-2-internals.md#q5-external-side-effects) · [Implement it](level-3-code-labs.md#q5-checkpoint-scoped-commit)

## Q6. What should happen when one stage produces records faster than the next can consume them?

**Starting point.** Operators exchange records through network buffers. A slow sink, skewed partition, or saturated CPU makes one consumer drain more slowly than its producers fill.

**What breaks.** Unbounded queues convert a throughput mismatch into memory exhaustion and enormous recovery time. Dropping arbitrary records silently changes results. Retrying faster adds more pressure.

**The question.** Where is capacity bounded, how does inability to acquire or recycle buffers propagate upstream, and which metrics distinguish healthy utilization from permanent debt?

**Philosophy:** make buffering finite and let exhausted capacity suspend production until downstream returns credit. Backpressure should follow the dependency path to an admission boundary.

**Warning:** backpressure protects memory; it does not create capacity or decide which business workload deserves admission.

[Overload and backpressure comparison](../library/comparisons/overload-and-backpressure.md) · [Go deeper](level-2-internals.md#q6-network-backpressure) · [Implement it](level-3-code-labs.md#q6-credit-buffer-pool)

## Q7. How can data processing and control work share a task without concurrent state mutation?

**Starting point.** One operator must process records while also handling timers, checkpoint actions, asynchronous completions, cancellation, and RPC-triggered control events.

**What breaks.** Letting every callback mutate operator state requires pervasive locks and permits snapshots between half-applied changes. Giving control work no scheduling path makes a busy input loop starve checkpoints and cancellation.

**The question.** Which thread is authoritative, how do other threads hand work to it, and where are safe yield points?

**Philosophy:** keep mutable operator logic on one task thread. Interleave the default input action with queued mailbox actions, so callbacks transfer commands rather than state ownership.

**Warning:** single-threaded ownership removes data races, not starvation; long record callbacks still block every mailbox action.

[Ownership and background work comparison](../library/comparisons/ownership-and-background-work.md) · [Go deeper](level-2-internals.md#q7-mailbox-ownership) · [Implement it](level-3-code-labs.md#q7-mailbox-loop)

## Q8. What information is required to restart a failed distributed dataflow correctly?

**Starting point.** A worker can disappear after consuming inputs, mutating state, emitting records, or preparing sink transactions. Replacement tasks may run on different machines and have new attempt identities.

**What breaks.** Restarting empty loses history. Restoring state without source positions replays an arbitrary prefix. Reusing stale messages from an earlier attempt lets a dead owner affect the new execution.

**The question.** Which completed checkpoint is authoritative, which execution region restarts, and how are stale attempts fenced?

**Philosophy:** recovery is a coordinated rollback to one completed epoch: restore operator and channel state, reset replayable sources, recover pending sink work, and issue new execution attempts.

**Warning:** replayable input and deterministic-enough operator behavior are part of the contract; an external non-replayable source cannot be repaired by checkpoint metadata.

[Go deeper](level-2-internals.md#q8-failure-recovery) · [Implement it](level-3-code-labs.md#q8-epoch-recovery)

## Q9. How can state move safely when the number of workers changes?

**Starting point.** A job needs more or fewer subtasks, but its state is partitioned among the old subtasks. The new topology must continue each key's history exactly once.

**What breaks.** Copying whole old task snapshots to new tasks duplicates or omits keys. Rehashing opaque state cannot reconstruct operator-list or broadcast semantics. Changing the key-group universe can make old snapshots unmappable.

**The question.** Which state unit is redistributed, how does each state kind declare its redistribution rule, and what limits later parallelism?

**Philosophy:** restore from a completed snapshot into a new assignment. Redistribute keyed state by stable key groups and operator state by explicit split, union, or broadcast semantics.

**Warning:** rescaling is recovery into a new topology, not live concurrent ownership transfer; state size and checkpoint bandwidth set its operational cost.

[Go deeper](level-2-internals.md#q9-state-rescaling) · [Implement it](level-3-code-labs.md#q9-state-redistribution)

## Q10. How should a stateful service choose between fast local access and scalable durable snapshots?

**Starting point.** Every record may read and update state, while periodic checkpoints must copy enough information to remote durable storage. State ranges from megabytes of counters to terabytes of keyed history.

**What breaks.** Heap objects are fast but increase garbage collection and full-snapshot cost. An embedded storage engine controls memory and enables incremental snapshots but adds serialization, compaction, native memory, and tuning debt. Durable storage on the hot path adds latency.

**The question.** Which representation serves live reads, which medium retains recovery images, and how are checkpoint duration, local recovery, and memory debt measured separately?

**Philosophy:** separate the live state backend from checkpoint storage. Choose the backend from state scale and access pattern, then choose durable storage from recovery and availability requirements.

**Warning:** “off-heap” does not mean free; block cache, write buffers, compaction, local disk, and remote upload are real capacity budgets.

[Go deeper](level-2-internals.md#q10-state-backend-selection) · [Implement it](level-3-code-labs.md#q10-incremental-state-manifest)

## Q11. How can stateful code be upgraded without losing the meaning of stored state?

**Starting point.** A deployment changes operator code, topology, serializer, or state type while durable snapshots still refer to the old operators and bytes.

**What breaks.** Auto-generated operator identities change after a harmless graph edit. A new serializer may read old bytes incorrectly. Removing state accidentally or changing maximum parallelism can make restoration impossible.

**The question.** Which identities remain stable across versions, who judges serializer compatibility, and when must migration be explicit rather than automatic?

**Philosophy:** treat a savepoint as a versioned data contract. Assign stable operator UIDs, preserve state names and serializer snapshots, test restore before rollout, and keep a rollback artifact.

**Warning:** a successful restore proves structural compatibility, not that new business logic interprets historical state correctly.

[Go deeper](level-2-internals.md#q11-stateful-upgrades) · [Implement it](level-3-code-labs.md#q11-versioned-state-migration)
