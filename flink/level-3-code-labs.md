# Apache Flink Source Study — Level 3: Code Labs

[Radar home](../README.md) · [Flink home](README.md) · [Level 1](level-1-philosophy.md) · [Level 2](level-2-internals.md)

These are mechanism-sized sketches, not production Flink replacements. Each exercise makes one invariant executable.

## Q1. Watermark valve

[Problem framing](level-1-philosophy.md#q1-how-can-a-system-make-time-based-decisions-when-records-arrive-out-of-order) · [Internals](level-2-internals.md#q1-event-time-progress)

```python
class WatermarkValve:
    def __init__(self, channels):
        self.wm = [-10**30] * channels
        self.active = [True] * channels
        self.output = -10**30

    def update(self, channel, watermark):
        self.wm[channel] = max(self.wm[channel], watermark)
        candidates = [w for w, active in zip(self.wm, self.active) if active]
        if candidates:
            self.output = max(self.output, min(candidates))
        return self.output

    def set_idle(self, channel, idle=True):
        self.active[channel] = not idle
        return self.update(channel, self.wm[channel])
```

**Handwrite:** add safe reactivation: a returning input below the last output must not move time backward or block forever. **Tests:** fast/slow inputs, duplicate watermarks, all idle, reactivation. **Invariant:** emitted watermarks are monotonic and never exceed the minimum active claim.

## Q2. Window lifecycle

[Problem framing](level-1-philosophy.md#q2-how-should-time-indexed-state-be-bounded-when-late-records-are-still-possible) · [Internals](level-2-internals.md#q2-windows-timers-and-late-data)

```python
def on_event(key, ts, value, watermark, size, lateness, state, late):
    start = (ts // size) * size
    end = start + size
    if watermark > end + lateness:
        late.append((key, ts, value))
        return
    state[(key, start)] = state.get((key, start), 0) + value

def on_watermark(wm, size, lateness, state, emit):
    for (key, start), total in list(state.items()):
        end = start + size
        if wm >= end:
            emit(key, start, total)       # insert or correction
        if wm > end + lateness:
            del state[(key, start)]       # final cleanup
```

**Handwrite:** track whether a result is initial or a correction. **Tests:** on-time, accepted-late, too-late, stalled watermark. **Invariant:** no window state survives its cleanup boundary.

## Q3. Key-group assignment

[Problem framing](level-1-philosophy.md#q3-how-can-many-workers-update-per-key-state-without-a-remote-lookup-for-every-record) · [Internals](level-2-internals.md#q3-keyed-state-ownership)

```python
def owner(key_hash, max_parallelism, parallelism):
    key_group = positive_murmur_hash(key_hash) % max_parallelism
    return key_group, key_group * parallelism // max_parallelism

def range_for(subtask, max_parallelism, parallelism):
    start = (subtask * max_parallelism + parallelism - 1) // parallelism
    end = ((subtask + 1) * max_parallelism - 1) // parallelism
    return range(start, end + 1)
```

**Handwrite:** a property test over several parallelisms. **Tests:** every group has one owner, ranges do not overlap, keys retain groups after rescale. **Invariant:** current parallelism changes owners, never key-group identity.

## Q4. Barrier snapshot

[Problem framing](level-1-philosophy.md#q4-how-can-a-distributed-computation-take-a-consistent-snapshot-while-records-keep-flowing) · [Internals](level-2-internals.md#q4-distributed-snapshots)

```python
def receive(channel, item, checkpoint, blocked, state, queues):
    if item == ("barrier", checkpoint):
        blocked.add(channel)
        if blocked == set(queues):
            handle = persist(state)
            forward(item)
            blocked.clear()
            return handle
    elif channel in blocked:
        queues[channel].append(item)
    else:
        apply(item, state)
```

**Handwrite:** an unaligned variant that persists queued/in-flight records instead of blocking channels. **Tests:** barrier order permutations and crash after local snapshot before acknowledgement. **Invariant:** every pre-cut record appears in operator or channel state exactly once.

## Q5. Checkpoint-scoped commit

[Problem framing](level-1-philosophy.md#q5-how-can-recovered-computation-agree-with-an-external-side-effect) · [Internals](level-2-internals.md#q5-external-side-effects)

```python
class CheckpointSink:
    def __init__(self, external):
        self.external = external
        self.current = external.begin()
        self.pending = {}

    def write(self, record): self.external.write(self.current, record)
    def snapshot(self, checkpoint_id):
        self.external.prepare(self.current)
        self.pending[checkpoint_id] = self.current
        self.current = self.external.begin()
        return dict(self.pending)
    def completed(self, checkpoint_id):
        for cid in sorted(list(self.pending)):
            if cid <= checkpoint_id:
                self.external.commit_idempotently(self.pending.pop(cid))
```

**Handwrite:** recovery for prepared transactions. **Tests:** crash before prepare, after prepare, during commit, and duplicate completion. **Invariant:** a transaction identity commits at most once even when notification repeats.

## Q6. Credit buffer pool

[Problem framing](level-1-philosophy.md#q6-what-should-happen-when-one-stage-produces-records-faster-than-the-next-can-consume-them) · [Internals](level-2-internals.md#q6-network-backpressure)

```python
class Channel:
    def __init__(self, buffers):
        self.free, self.inflight = buffers, []
    def send(self, record):
        if not self.free:
            return False
        segment = self.free.pop()
        segment.write(record)
        self.inflight.append(segment)
        return True
    def consume(self):
        segment = self.inflight.pop(0)
        record = segment.read()
        segment.clear()
        self.free.append(segment)         # returned credit
        return record
```

**Handwrite:** fair allocation across two channels sharing a global pool. **Tests:** slow consumer, zero credit, recycled segment, cancellation while blocked. **Invariant:** in-flight records cannot exceed granted buffers.

## Q7. Mailbox loop

[Problem framing](level-1-philosophy.md#q7-how-can-data-processing-and-control-work-share-a-task-without-concurrent-state-mutation) · [Internals](level-2-internals.md#q7-mailbox-ownership)

```python
def run(mailbox, input_gate, operator, cancelled):
    while not cancelled():
        while mailbox.has_urgent():
            mailbox.take_urgent()()
        if mailbox.has_mail():
            mailbox.take()()
        elif input_gate.ready():
            operator.process(input_gate.next())
        else:
            mailbox.wait_for_mail_or(input_gate)
```

**Handwrite:** an async lookup whose worker posts `(attempt_id, result)` and whose mail rejects stale attempts. **Tests:** checkpoint mail amid records, cancellation, long callback, mail flood. **Invariant:** only the task thread invokes mutable operator logic.

## Q8. Epoch recovery

[Problem framing](level-1-philosophy.md#q8-what-information-is-required-to-restart-a-failed-distributed-dataflow-correctly) · [Internals](level-2-internals.md#q8-failure-recovery)

```python
def recover(completed, graph):
    epoch = graph.next_attempt_epoch()
    for task in graph.restart_region(completed.failed_task):
        task.cancel_old_attempts()
        task.restore(completed.operator_state[task.operator_id])
        task.restore_channels(completed.channel_state.get(task.id, []))
        task.start(epoch)
    for source in graph.sources:
        source.seek(completed.source_positions[source.id])
```

**Handwrite:** reject acknowledgements whose attempt epoch differs from the current execution. **Tests:** state handle missing, stale acknowledgement, repeated failure, region dependency. **Invariant:** all restarted components agree on one completed checkpoint and new attempt epoch.

## Q9. State redistribution

[Problem framing](level-1-philosophy.md#q9-how-can-state-move-safely-when-the-number-of-workers-changes) · [Internals](level-2-internals.md#q9-state-rescaling)

```python
def redistribute_key_groups(handles, max_parallelism, new_parallelism):
    result = [[] for _ in range(new_parallelism)]
    for handle in handles:
        for key_group in handle.key_groups:
            target = key_group * new_parallelism // max_parallelism
            result[target].append(handle.slice(key_group))
    return result

def redistribute_list(items, new_parallelism):
    return [[x for i, x in enumerate(items) if i % new_parallelism == t]
            for t in range(new_parallelism)]
```

**Handwrite:** union and broadcast redistribution. **Tests:** scale 2→5→1, empty tasks, max-parallelism violation. **Invariant:** split state has one new owner; union/broadcast follows its declared multiplicity.

## Q10. Incremental state manifest

[Problem framing](level-1-philosophy.md#q10-how-should-a-stateful-service-choose-between-fast-local-access-and-scalable-durable-snapshots) · [Internals](level-2-internals.md#q10-state-backend-selection)

```python
def checkpoint(files, previous_manifest, upload):
    previous = {f.digest: f for f in previous_manifest.files}
    manifest = []
    for local in files:
        digest = sha256(local)
        remote = previous.get(digest) or upload(local, digest)
        manifest.append(remote)
    return durable_write_manifest(manifest)
```

**Handwrite:** reference counting so deleting an old checkpoint cannot delete a shared file. **Tests:** no change, one changed file, failed upload, manifest publish failure. **Invariant:** a completed manifest references only durable files, and shared files live until their final reference disappears.

## Q11. Versioned state migration

[Problem framing](level-1-philosophy.md#q11-how-can-stateful-code-be-upgraded-without-losing-the-meaning-of-stored-state) · [Internals](level-2-internals.md#q11-stateful-upgrades)

```python
def restore(snapshot, job):
    for uid, old_state in snapshot.by_operator_uid.items():
        operator = job.require_uid(uid)
        verdict = operator.serializer.compatibility(old_state.serializer_snapshot)
        if verdict == "compatible":
            operator.attach(old_state.bytes)
        elif verdict == "migrate":
            operator.attach(operator.serializer.migrate(old_state.bytes))
        else:
            raise IncompatibleState(uid)
```

**Handwrite:** a migration from integer cents to a record `{currency, minor_units}` with an explicit default currency. **Tests:** renamed UID, missing state, compatible read, migration, rollback. **Invariant:** no state is silently discarded or reinterpreted.
