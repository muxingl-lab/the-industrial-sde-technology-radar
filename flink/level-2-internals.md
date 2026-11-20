# Apache Flink Source Study — Level 2: Internals

[Radar home](../README.md) · [Flink home](README.md) · [Level 1](level-1-philosophy.md) · [Level 3](level-3-code-labs.md) · [Source map](source-map.md)

Level 2 follows the runtime workflow and makes the interview contract explicit. API spelling varies across DataStream generations; the invariants do not.

## Q1. Event-time progress

[Problem framing](level-1-philosophy.md#q1-how-can-a-system-make-time-based-decisions-when-records-arrive-out-of-order) · [Code lab](level-3-code-labs.md#q1-watermark-valve)

A source assigns timestamps and periodically emits a watermark according to a `WatermarkStrategy`. The claim is monotonic: after watermark `W`, the source does not ordinarily expect an event with timestamp at or below `W`. At a multi-input task, `StatusWatermarkValve` stores per-subpartition progress and emits a new minimum across active inputs. An idle declaration removes a silent input from that minimum; activity must rejoin without moving output time backward.

The central invariant is `output_watermark <= min(active_input_watermarks)` and output never decreases. Bounded-out-of-orderness is a latency/completeness policy: roughly `largest_seen_timestamp - tolerated_delay`, not a measurement of real network delay. Watermark alignment can throttle a source that races far ahead so downstream state does not grow from excessive skew.

**Failure modes:** idle detection mistakes a merely slow partition for dead; clock errors create absurd timestamps; one permanently active but stalled input freezes progress; watermark generation after a repartition loses per-split context.

**Interview follow-ups:** Why is the maximum input watermark unsafe? What happens when all inputs are idle? How does event time differ from ingestion and processing time? Which metric reveals watermark lag?

## Q2. Windows, timers, and late data

[Problem framing](level-1-philosophy.md#q2-how-should-time-indexed-state-be-bounded-when-late-records-are-still-possible) · [Code lab](level-3-code-labs.md#q2-window-lifecycle)

The window assigner maps an event into one or more window namespaces. `WindowOperator` selects the key, loads namespaced state, applies the element, and lets a trigger register event-time or processing-time timers. When a timer fires, the trigger may emit, purge, or continue. Event-time cleanup occurs after `window.maxTimestamp + allowedLateness`; an element later than that can be dropped or sent to a side output.

An aggregate can emit an initial result at the window boundary and a correction during allowed lateness. The sink must therefore accept updates, retractions, or a versioned result key. Cleanup must remove window contents, trigger state, and timers. Session windows add merging: state and timers from old namespaces must become one logical window.

**Failure modes:** no watermark means no event-time cleanup; a global window has no natural end; allowed lateness multiplies retained state; a sink appends corrections as duplicate facts; timer storms create latency spikes.

**Interview follow-ups:** Trigger versus eviction? Event-time versus processing-time timer? Why is a side output useful? How would you estimate window-state bytes under skew?

## Q3. Keyed-state ownership

[Problem framing](level-1-philosophy.md#q3-how-can-many-workers-update-per-key-state-without-a-remote-lookup-for-every-record) · [Code lab](level-3-code-labs.md#q3-key-group-assignment)

Partitioning computes `keyGroup = murmurHash(key.hashCode) % maxParallelism`; the current subtask follows `keyGroup * parallelism / maxParallelism`. Each subtask owns a contiguous `KeyGroupRange`. Before invoking user code the runtime establishes the current key, so `ValueState`, `MapState`, and timers address `(operator, key-group, key, namespace, state-name)` in the selected backend.

`maxParallelism` fixes the key-group universe and therefore the finest future redistribution unit. Current parallelism changes which ranges a subtask owns, not which key group a key belongs to. Only the owner mutates its keyed state on the task thread; checkpoints serialize handles grouped so restore can select the new owner's ranges.

**Failure modes:** unstable `hashCode`; mutable keys; key skew; changing max parallelism without a migration; non-keyed external state pretending to share the same ownership guarantee.

**Interview follow-ups:** Why not hash directly modulo parallelism? Why contiguous ranges? Can one hot key be split? What is the difference between keyed and operator state?

## Q4. Distributed snapshots

[Problem framing](level-1-philosophy.md#q4-how-can-a-distributed-computation-take-a-consistent-snapshot-while-records-keep-flowing) · [Code lab](level-3-code-labs.md#q4-barrier-snapshot)

`CheckpointCoordinator` allocates an ID, determines source/task trigger targets, and asks sources to snapshot their positions and inject barriers. A one-input operator snapshots when its barrier arrives. For an aligned multi-input checkpoint, the task blocks channels that delivered the barrier, continues draining older records from other channels, then snapshots and forwards the barrier after all channels align. Snapshot work may produce asynchronous durable handles; tasks acknowledge those handles to the coordinator. Only all required acknowledgements make a `CompletedCheckpoint`, after which completion notifications may release external commits.

Alignment keeps post-cut records out of operator state without recording channel contents, but slow channels can make barrier alignment inherit backpressure. Unaligned checkpoints overtake alignment and capture in-flight network buffers as channel state. They shorten time to establish the cut while increasing bytes, I/O, and restore work. Concurrent-checkpoint limits, timeouts, minimum pauses, and retained history bound control-plane and storage debt.

**Failure modes:** one lost acknowledgement; checkpoint timeout during overload; asynchronous state upload failure; coordinator failover; subsumed pending checkpoints; channel state too large to restore quickly.

**Interview follow-ups:** Why are barriers not global locks? What exactly is captured in an unaligned checkpoint? When can incremental state still produce a slow checkpoint? Checkpoint versus savepoint?

## Q5. External side effects

[Problem framing](level-1-philosophy.md#q5-how-can-recovered-computation-agree-with-an-external-side-effect) · [Code lab](level-3-code-labs.md#q5-checkpoint-scoped-commit)

The classic two-phase sink path makes the protocol visible. Records write to a current external transaction. On snapshot, the sink pre-commits that transaction, stores its handle as pending checkpoint state, and begins another. A completed-checkpoint notification commits transactions covered by that checkpoint; recovery aborts or commits restored transactions according to the connector contract. Modern Sink API implementations may separate writer, committer, and global committer, but still need checkpoint-correlated committables and idempotent recovery.

The runtime's atomic boundary is its completed checkpoint. The external system must add durable transactions or idempotency. Transaction timeout must exceed checkpoint interval plus worst credible recovery. Commit must tolerate repeated notifications and late completion from an older attempt must be fenced.

**Failure modes:** commit succeeds but acknowledgement is lost; transaction expires during outage; sink cannot fence prior producers; source participates in checkpointing but sink does not; side effects occur in user code before a checkpoint boundary.

**Interview follow-ups:** Exactly-once processing versus exactly-once effect? Why commit on completion rather than snapshot? What if the sink has no transactions? How does an outbox change the boundary?

## Q6. Network backpressure

[Problem framing](level-1-philosophy.md#q6-what-should-happen-when-one-stage-produces-records-faster-than-the-next-can-consume-them) · [Code lab](level-3-code-labs.md#q6-credit-buffer-pool)

TaskManagers reserve a finite global pool of fixed-size network segments. Input gates and result partitions request local buffer pools with required and optional capacity. A downstream channel advertises available receive buffers as credit; upstream may send data only within credit. When a consumer slows, it recycles fewer segments, credit falls, upstream output cannot acquire buffers, and the task eventually stops consuming its own input. Pressure therefore travels along the graph rather than accumulating an unbounded queue.

This is flow control, not workload admission. The job can remain permanently backpressured, checkpoints can become slow, and unrelated edges can contend for the global pool. Useful signals include busy/backpressured/idle time, buffer usage, pool wait, output queue length, throughput, and checkpoint alignment duration.

**Failure modes:** buffer starvation or deadlock from bad minimum allocation; one skewed channel monopolizes optional buffers; increasing buffers hides overload and increases in-flight recovery state; a blocking sink turns transient pressure permanent.

**Interview follow-ups:** What is credit? Where does the producer block? Why do more buffers sometimes worsen latency? How does backpressure interact with aligned and unaligned checkpoints?

## Q7. Mailbox ownership

[Problem framing](level-1-philosophy.md#q7-how-can-data-processing-and-control-work-share-a-task-without-concurrent-state-mutation) · [Code lab](level-3-code-labs.md#q7-mailbox-loop)

`StreamTask` runs operator callbacks on its task thread. `MailboxProcessor` repeatedly runs queued mails and a default action that advances input. Other threads enqueue actions—checkpoint coordination, timer or asynchronous completion, cancellation—rather than invoking user operators concurrently. A priority mechanism lets urgent control work precede ordinary mail, and the default action can suspend when input is unavailable.

The invariant is thread confinement of operator state, not “the process has one thread.” Network, state snapshot, RPC, and I/O workers exist, but they transfer immutable results or commands at a mailbox boundary. Cooperative yielding is essential: long user callbacks, blocking I/O, or loops without a yield delay timers, checkpoint barriers, and cancellation.

**Failure modes:** callback mutates captured state off-thread; blocking user function starves mailbox; unbounded mail production; cancellation arrives after an async completion; priority mail starves data.

**Interview follow-ups:** Why not lock operator state? What runs asynchronously during a checkpoint? What is the linearization point for a callback? How do you fence stale completions?

## Q8. Failure recovery

[Problem framing](level-1-philosophy.md#q8-what-information-is-required-to-restart-a-failed-distributed-dataflow-correctly) · [Code lab](level-3-code-labs.md#q8-epoch-recovery)

A completed checkpoint contains operator-state handles, source positions, optional channel state, and metadata mapping state to operator identities. The execution graph tracks vertices and execution attempts. On failure, the configured failover strategy determines the restart set; affected attempts are cancelled, new attempts receive restored state, sources seek to checkpointed positions, and sinks recover pending transactions. Restart strategies control retry count and delay; scheduler state also must survive leadership changes through durable job/checkpoint metadata.

Correctness depends on fencing. Messages, acknowledgements, and asynchronous completions identify the job, checkpoint, execution attempt, or coordinator epoch so old owners cannot mutate the new run. Regional recovery can restart less work only when blocking/pipelined dependencies and replay boundaries make the selected region self-consistent.

**Failure modes:** corrupt or missing checkpoint handles; non-replayable source; serializer incompatibility; restart loop that overloads dependencies; nondeterministic external call repeated after rollback; stale attempt acknowledgement.

**Interview follow-ups:** What is restored versus recomputed? Global versus regional failover? Why retain several checkpoints? How should restart backoff interact with an unhealthy dependency?

## Q9. State rescaling

[Problem framing](level-1-philosophy.md#q9-how-can-state-move-safely-when-the-number-of-workers-changes) · [Code lab](level-3-code-labs.md#q9-state-redistribution)

Rescaling normally stops or restarts a job from a checkpoint/savepoint with new parallelism. `StateAssignmentOperation` maps old operator-state handles to new execution vertices. Keyed state is sliced or referenced by key-group range; the formula assigns every key group to exactly one new subtask. Operator list state may be round-robin split, union state gives every subtask the complete union, and broadcast state must remain identical across tasks.

The coordinator and source may also redistribute split ownership and coordinator state. Stable operator UIDs connect new graph vertices to old state. Maximum parallelism bounds new keyed parallelism; changing it is a state migration rather than an ordinary rescale. Large state can be accelerated by incremental/shared files and local recovery, but shared handles require reference-safe cleanup.

**Failure modes:** missing UID; parallelism exceeds max; duplicate union state causes duplicate work; uneven key groups; savepoint points at inaccessible storage; shared state discarded while referenced.

**Interview follow-ups:** Why is rescaling not online repartitioning? Split versus union list state? What determines movement volume? How would you validate no key group is missing or duplicated?

## Q10. State-backend selection

[Problem framing](level-1-philosophy.md#q10-how-should-a-stateful-service-choose-between-fast-local-access-and-scalable-durable-snapshots) · [Code lab](level-3-code-labs.md#q10-incremental-state-manifest)

A state backend owns live state access and produces snapshot handles; checkpoint storage owns durable bytes and metadata. Heap state keeps Java objects and usually snapshots serialized state, favoring small state and fast access but sharing heap and GC. RocksDB state stores serialized keys and values in an embedded LSM engine, trading access/serialization and compaction cost for controlled memory, disk spill, and incremental checkpoint files. ForSt targets disaggregated state access with different latency and storage assumptions.

Incremental checkpoints upload new immutable files and reference shared files from earlier checkpoints. This reduces repeated bytes when churn is modest, not necessarily checkpoint metadata or recovery latency. Local recovery retains a local copy as an optimization; durable remote storage remains the authority after machine loss. Monitor live state bytes, managed/native memory, compaction, local disk, changed checkpoint bytes, upload duration, and restore time separately.

**Failure modes:** native memory exceeds container accounting; compaction competes with record processing; high churn defeats incremental reuse; remote storage throttles; local disk loss exposes slow full restore.

**Interview follow-ups:** Backend versus checkpoint storage? Incremental versus full snapshot? Why can RocksDB be slower but safer at scale? What workload favors heap state?

## Q11. Stateful upgrades

[Problem framing](level-1-philosophy.md#q11-how-can-stateful-code-be-upgraded-without-losing-the-meaning-of-stored-state) · [Code lab](level-3-code-labs.md#q11-versioned-state-migration)

A controlled upgrade takes a savepoint or retained checkpoint, deploys a new job graph, matches state by stable operator UID and state name, asks serializer snapshots whether old bytes are compatible, and restores or runs a declared migration. Topology edits may add stateless operators freely, but removing a stateful operator, changing max parallelism, altering state type, or changing UID requires an explicit compatibility decision. Savepoint location and connector/source semantics must remain valid for the new deployment.

The rollout should restore and validate in staging, compare state counts and representative outputs, preserve the old artifact and snapshot, and switch traffic only after readiness. Schema compatibility covers bytes; semantic compatibility requires application tests. A migration that rewrites terabytes belongs in an offline or bounded operational plan, not hidden in startup.

**Failure modes:** generated UID changes; serializer reports migration but startup exceeds timeout; state is silently dropped; source mapping changes and replays data; new logic reinterprets old enum or unit incorrectly.

**Interview follow-ups:** Checkpoint versus savepoint for upgrades? What does a serializer snapshot contain? Why are explicit UIDs operationally important? How do you roll back after new outputs escape?
