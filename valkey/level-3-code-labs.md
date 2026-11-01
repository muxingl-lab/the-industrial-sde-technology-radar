# Valkey Source Study — Level 3: Code Labs

[Radar home](../README.md) · [Valkey home](README.md) · [Level 1](level-1-philosophy.md) · [Level 2](level-2-internals.md)

These labs isolate invariants from the production C implementation. They are not drop-in Valkey replacements.

## Q1. Owner thread with adaptive I/O workers
[Philosophy](level-1-philosophy.md#q1-how-can-connection-work-run-in-parallel-without-giving-mutable-state-several-owners) · [Interview answer](level-2-internals.md#q1-adaptive-io-workers)

```java
record IoJob(long clientId, long generation, Kind kind, byte[] bytes) {}
record IoDone(long clientId, long generation, Kind kind, Object result) {}

void ownerTurn() {
    for (IoDone done; (done = completions.poll()) != null;) {
        Client c = clients.get(done.clientId());
        if (c == null || c.generation != done.generation()) continue;
        c.finishIo(done);                 // owner changes lifecycle state
        if (done.kind() == Kind.READ) executeParsedCommands(c);
    }
    resizeWorkers(queueDepth.average(), mainThread.utilization());
}
```

**Handwrite:** define client states for idle/read-pending/read-ready/write-pending/closing. Add a bounded submission queue, cancellation, and shutdown drain.

**Fault test:** randomly close and reuse client IDs while completions are delayed. Assert that stale generations never execute or write, each accepted command executes at most once, and no client has simultaneous incompatible jobs.

## Q2. Staged prefetch batch
[Philosophy](level-1-philosophy.md#q2-when-can-batching-independent-requests-hide-memory-latency) · [Interview answer](level-2-internals.md#q2-staged-software-prefetch)

```c
for (int i = 0; i < n; i++)
    __builtin_prefetch(bucket_for(hash(keys[i])), 0, 1);
for (int i = 0; i < n; i++) {
    entries[i] = find_entry(keys[i]);
    if (entries[i]) __builtin_prefetch(entries[i]->value, 0, 1);
}
for (int i = 0; i < n; i++)
    execute_in_original_order(commands[i], entries[i]);
```

**Handwrite:** add eligibility checks, duplicate keys, client removal, and a maximum wait timer so a partial batch cannot wait forever.

**Benchmark:** compare no prefetch, entry-only, and entry-plus-value for batch sizes 1–128 under hot, uniform, and Zipfian keys. Report LLC misses, throughput, P50, and P99; do not infer benefit from throughput alone.

## Q3. Snapshot plus change stream
[Philosophy](level-1-philosophy.md#q3-how-can-a-replica-receive-a-large-snapshot-without-falling-behind-on-new-writes) · [Interview answer](level-2-internals.md#q3-dual-channel-full-synchronization)

```java
record Boundary(UUID producer, long endOffset) {}

void synchronize(SnapshotChannel bulk, ChangeChannel live, long maxBuffered) {
    Boundary b = bulk.readBoundary();
    Future<State> base = workers.submit(() -> bulk.receiveAndLoad(b));
    while (!base.isDone()) {
        Change change = live.readNext();
        require(change.producer().equals(b.producer()));
        if (!pending.offer(change, maxBuffered)) abortBoth("catch-up overflow");
    }
    state.install(base.join());
    pending.drainContiguouslyFrom(b.endOffset() + 1, state::apply);
}
```

**Handwrite:** add checksums, reconnect identity, offset-gap detection, idempotent abort, and a terminal transition that publishes readiness only after the join.

**Fault test:** cut either channel at every transition, corrupt the snapshot, duplicate a change, and overflow the buffer. The result must be a correct connected replica or an explicit failed state—never partial readiness.

## Q4. Fenced range migration
[Philosophy](level-1-philosophy.md#q4-how-can-ownership-of-many-live-partitions-move-as-one-atomic-operation) · [Interview answer](level-2-internals.md#q4-atomic-slot-range-migration)

```java
record Migration(UUID job, long generation, Set<Integer> slots,
                 Phase phase, long snapshotOffset, long ackOffset) {}

void grantHandoff(Migration m, long sourceTail) {
    require(m.phase() == Phase.WRITES_PAUSED);
    require(sourceTail - m.ackOffset() <= maxFinalLagBytes);
    topology.compareAndSetOwner(m.slots(), source, target, m.generation());
    journal.append(new Granted(m.job(), m.generation(), sourceTail));
}
```

**Handwrite:** build export/import transition tables, timeouts, cancellation, persisted job recovery, and topology CAS fencing. State which side may accept writes in every phase.

**Fault test:** crash source, destination, and coordinator before and after the ownership CAS. Replay the journal and assert one owner, no acknowledged-write loss, and no success reported for an incomplete range.

## Q5. Adaptive deadline index
[Philosophy](level-1-philosophy.md#q5-how-should-deadlines-be-indexed-for-items-nested-inside-a-larger-object) · [Interview answer](level-2-internals.md#q5-fine-grained-expiration-index)

```java
final class ExpiringHash {
    private final Map<String, Value> fields = new HashMap<>();
    private DeadlineIndex deadlines = DeadlineIndex.empty();

    Value get(String field, long now) {
        Long deadline = deadlines.deadlineOf(field);
        if (deadline != null && deadline <= now) {
            fields.remove(field);
            deadlines.remove(field, deadline);
            return null;
        }
        return fields.get(field);
    }

    int expireDue(long now, int budget) {
        int removed = 0;
        while (removed < budget && deadlines.earliestDeadline() <= now) {
            DeadlineEntry e = deadlines.popEarliest();
            if (fields.remove(e.field()) != null) removed++;
        }
        return removed;
    }
}
```

**Handwrite:** implement representation changes `EMPTY → SINGLE → SORTED_VECTOR → BUCKET_TREE`, TTL replacement, and downgrade policy. Include peak memory during conversion.

**Property test:** compare randomized set/get/expire/time-advance operations with a simple reference scan. Assert that no overdue field is visible, live fields are not removed, index membership agrees with TTL metadata, and one active pass removes at most its budget.

## Graduation exercise

Build an ordered in-memory request server with owner-thread mutation, adaptive I/O workers, staged key prefetch, bounded dual-stream snapshot recovery, and nested-field TTLs. Submit ownership invariants, state-transition tables, fault injection, P50/P99 results, and memory-debt graphs.
