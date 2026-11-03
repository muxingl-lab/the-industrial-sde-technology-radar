# Feast Source Study — Level 3: Code Labs

[Radar home](../README.md) · [Feast home](README.md) · [Level 1](level-1-philosophy.md) · [Level 2](level-2-internals.md)

The examples use Python to make temporal and distributed invariants visible. They are teaching mechanisms, not replacement Feast providers.

## Q1. Point-in-time join

[Philosophy](level-1-philosophy.md#q1-how-can-training-reconstruct-only-what-was-knowable-at-each-historical-decision-time) · [Interview answer](level-2-internals.md#q1-point-in-time-retrieval)

```python
def as_of(entity_rows, feature_rows, ttl):
    out = []
    for entity in entity_rows:
        candidates = [f for f in feature_rows
            if f["entity_id"] == entity["entity_id"]
            and entity["ts"] - ttl <= f["event_ts"] <= entity["ts"]]
        out.append(max(candidates, key=lambda f: f["event_ts"], default=None))
    return out
```

**Handwrite:** add created-time filtering and deterministic tie-breaking. **Test:** a future row, a row just outside TTL, late-created data, and two examples for the same entity.

## Q2. Contract fingerprint

[Philosophy](level-1-philosophy.md#q2-how-can-one-feature-retain-the-same-meaning-in-training-and-online-serving) · [Interview answer](level-2-internals.md#q2-feature-contract)

```python
import hashlib, json

def contract_id(spec):
    semantic = {k: spec[k] for k in (
        "entities", "features", "types", "source", "event_time",
        "ttl", "transform", "defaults")}
    encoded = json.dumps(semantic, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()
```

**Handwrite:** classify compatible versus breaking changes. **Test:** documentation edits preserve the ID; a TTL or transform change does not.

## Q3. Resumable materializer

[Philosophy](level-1-philosophy.md#q3-how-should-a-large-offline-to-online-materialization-survive-interruption) · [Interview answer](level-2-internals.md#q3-materialization)

```python
def materialize(start, end, step, read, upsert, checkpoint):
    cursor = checkpoint.load() or start
    while cursor < end:
        next_cursor = min(cursor + step, end)
        rows = read(cursor, next_cursor)
        upsert(rows)                 # idempotent or timestamp guarded
        checkpoint.compare_and_set(cursor, next_cursor)
        cursor = next_cursor
```

**Handwrite:** recover when the process dies after `upsert` but before checkpointing. **Test:** inject a failure at every line and compare final online state with one uninterrupted run.

## Q4. Timestamp-guarded upsert

[Philosophy](level-1-philosophy.md#q4-how-should-an-online-store-handle-an-older-update-that-arrives-after-a-newer-one) · [Interview answer](level-2-internals.md#q4-out-of-order-updates)

```python
class OnlineRow:
    def __init__(self): self.value, self.version = None, None
    def upsert(self, value, version):
        if self.version is None or version > self.version:
            self.value, self.version = value, version
            return True
        return False
```

The comparison and write must be one storage operation, such as a transaction or Redis script—not this unguarded in-memory shape across processes.

**Handwrite:** add versioned tombstones. **Test:** randomize update arrival order and assert that the maximum version wins.

## Q5. Parity harness

[Philosophy](level-1-philosophy.md#q5-where-should-a-feature-transformation-run) · [Interview answer](level-2-internals.md#q5-transformation-placement)

```python
def assert_parity(fixtures, offline_transform, online_transform, tolerance=1e-9):
    for case in fixtures:
        a, b = offline_transform(case), online_transform(case)
        if a is None or b is None:
            assert a is b, case
        else:
            assert abs(a - b) <= tolerance, (case, a, b)
```

**Handwrite:** compare structured outputs and timestamps. **Test:** nulls, time zones, window boundaries, floating-point extremes, and old contract versions.

## Q6. Plan and apply

[Philosophy](level-1-philosophy.md#q6-how-should-metadata-and-infrastructure-change-without-creating-a-split-brain-schema) · [Interview answer](level-2-internals.md#q6-metadata-rollout)

```python
def apply(plan, provider, registry):
    token = registry.acquire_lease(plan.project, plan.expected_generation)
    try:
        provider.prepare(plan.infrastructure)
        provider.verify_ready(plan.infrastructure)
        registry.publish(plan.metadata, expected=plan.expected_generation)
    finally:
        registry.release_lease(token)
```

**Handwrite:** add rollback for a registry publish failure while keeping backward-compatible infrastructure. **Test:** stale generation, concurrent apply, readiness failure, and expired lease.

## Q7. Capability gate

[Philosophy](level-1-philosophy.md#q7-how-can-a-pluggable-storage-abstraction-remain-honest-about-backend-guarantees) · [Interview answer](level-2-internals.md#q7-provider-capabilities)

```python
REQUIRED = {"created_time_filter", "conditional_upsert"}

def validate_repository(provider, required=REQUIRED):
    missing = required - provider.capabilities()
    if missing:
        raise ValueError(f"provider lacks required semantics: {sorted(missing)}")
```

**Handwrite:** attach semantic versions and tested limits to capabilities. **Test:** deployment fails closed rather than silently dropping created-time filtering.

## Q8. Outbox state machine

[Philosophy](level-1-philosophy.md#q8-what-should-happen-when-one-logical-feature-write-targets-two-stores) · [Interview answer](level-2-internals.md#q8-cross-store-writes)

```python
def deliver(intent, online, offline, journal):
    if not intent.online_done:
        online.put(intent.key, intent.value, idempotency_key=intent.id)
        journal.mark(intent.id, "online_done")
    if not intent.offline_done:
        offline.append(intent.key, intent.value, idempotency_key=intent.id)
        journal.mark(intent.id, "offline_done")
    journal.mark(intent.id, "complete")
```

**Handwrite:** define recovery from an uncertain timeout after a destination accepted the write. **Test:** duplicate delivery and every partial-failure ordering.

## Q9. Freshness evaluator

[Philosophy](level-1-philosophy.md#q9-how-do-you-know-whether-served-features-are-fresh-and-semantically-correct) · [Interview answer](level-2-internals.md#q9-feature-observability)

```python
def evaluate(value_meta, policy, now):
    age = now - value_meta.event_ts
    return {
        "fresh": age <= policy.max_age,
        "age_seconds": age.total_seconds(),
        "contract_match": value_meta.contract_id == policy.contract_id,
        "materialized_through": value_meta.watermark,
    }
```

**Handwrite:** distinguish “source produced no event” from “pipeline failed to ingest one.” **Test:** stale event time with a fresh request time must still alert.
