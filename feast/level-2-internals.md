# Feast Source Study — Level 2: Internals and Interviews

[Radar home](../README.md) · [Feast home](README.md) · [Level 1](level-1-philosophy.md) · [Level 3](level-3-code-labs.md) · [Source map](source-map.md)

## Q1. Point-in-time retrieval

[Philosophy](level-1-philosophy.md#q1-how-can-training-reconstruct-only-what-was-knowable-at-each-historical-decision-time) · [Code lab](level-3-code-labs.md#q1-point-in-time-join)

For every entity row at time T, retrieve the newest feature row whose event timestamp is at or before T and, when a TTL exists, after T minus TTL. Partition by entity keys, order eligible rows by event time, and select one row per entity example. Created timestamps can additionally exclude corrections that were not yet known, but support is backend-dependent and Feast does not enable that filter universally by default.

**Invariant:** no selected feature event occurs after its entity timestamp, and every value satisfies the feature view's entity and TTL contract.

**Follow-ups.** Event time describes the domain fact; created/ingestion time describes when the platform learned it. Late data can legitimately change a recomputed training set. Duplicate timestamps need deterministic tie-breaking. Test the generated query against a hand-built temporal fixture.

## Q2. Feature contract

[Philosophy](level-1-philosophy.md#q2-how-can-one-feature-retain-the-same-meaning-in-training-and-online-serving) · [Code lab](level-3-code-labs.md#q2-contract-fingerprint)

A feature contract includes project, entity keys, feature name and type, source, event-time column, TTL, transformation, default/null behavior, ownership, and version. Historical and online retrieval resolve definitions from the registry, while feature services select a stable serving projection. Clients should request a named/versioned service rather than assemble ad hoc columns.

**Invariant:** one contract version maps a logical feature to compatible offline and online representations. A breaking semantic change receives a new identity or an explicit coordinated migration.

**Follow-ups.** Schema equality does not imply semantic equality. Run offline-online parity samples with known timestamps. Record the embedding/model or upstream table version when it changes feature meaning. Cache invalidation must be included in rollout time.

## Q3. Materialization

[Philosophy](level-1-philosophy.md#q3-how-should-a-large-offline-to-online-materialization-survive-interruption) · [Code lab](level-3-code-labs.md#q3-resumable-materializer)

Materialization chooses a time interval, queries the offline store for the latest eligible value per entity, and asks the provider to write batches to the online store. Incremental materialization begins after recorded progress. A robust operator subdivides intervals, makes writes idempotent or timestamp-guarded, records a chunk complete only after its writes succeed, and can replay uncertain chunks.

**Invariant:** progress never advances beyond durably applied work. Retrying a completed or uncertain chunk cannot replace a newer online value with an older one.

**Follow-ups.** Registry progress and backend rows are not generally one transaction. Use overlap windows for late data, but combine them with timestamp guards. Bound batch size, retries, and concurrency. Reconcile counts and maximum event timestamps after completion.

## Q4. Out-of-order updates

[Philosophy](level-1-philosophy.md#q4-how-should-an-online-store-handle-an-older-update-that-arrives-after-a-newer-one) · [Code lab](level-3-code-labs.md#q4-timestamp-guarded-upsert) · [Redis online store](https://github.com/feast-dev/feast/blob/2dfb9e6d1a37719fd11028d916094050f1cdd552/sdk/python/feast/infra/online_stores/redis.py)

Attach an event timestamp or monotonic source version to every row. At the storage boundary, atomically replace the current row only if the incoming version is newer, or define deterministic equality behavior. Feast's Redis implementation normally performs timestamp-aware deduplication; a configured fast path can skip it to gain throughput.

**Invariant:** after any arrival order, the stored version is the maximum accepted version under the declared ordering.

**Follow-ups.** A client-side read-compare-write races. Clock timestamps from different producers may not be totally ordered; source offsets or logical versions can be safer. Tombstones also need versions or deleted values can reappear.

## Q5. Transformation placement

[Philosophy](level-1-philosophy.md#q5-where-should-a-feature-transformation-run) · [Code lab](level-3-code-labs.md#q5-parity-harness)

Classify inputs as historical source data, precomputed feature data, request data, or external online data. Batch transformations belong in reproducible offline pipelines when they can be materialized. Request-dependent transformations belong near online retrieval and must have strict CPU and dependency budgets. A shared implementation or generated expression reduces duplication, but parity fixtures verify actual values.

**Invariant:** for the same logical inputs and timestamp, offline and online paths produce equivalent values within a declared numerical tolerance.

**Follow-ups.** Pin libraries and locale/time-zone behavior. Define null and default semantics. Avoid network calls in an on-demand transform unless their latency, caching, and failure policy are part of the serving SLO.

## Q6. Metadata rollout

[Philosophy](level-1-philosophy.md#q6-how-should-metadata-and-infrastructure-change-without-creating-a-split-brain-schema) · [Code lab](level-3-code-labs.md#q6-plan-and-apply) · [FeatureStore](https://github.com/feast-dev/feast/blob/2dfb9e6d1a37719fd11028d916094050f1cdd552/sdk/python/feast/feature_store.py)

Diff desired definitions against the registry, validate dependencies, produce an infrastructure plan, create backward-compatible resources, publish metadata, wait for caches and servers to observe the version, migrate data, shift clients, and retire old resources last. The exact order changes by compatibility direction. Feast `apply` coordinates several steps, but the source retains locking and transactional boundaries as provider concerns.

**Invariant:** every active reader version has compatible metadata and infrastructure throughout the rollout.

**Follow-ups.** Registry cache TTL bounds neither provider readiness nor client rollout. Use generation IDs and readiness states. Serialize conflicting applies or use optimistic concurrency. Rollback may require preserving both schema and data.

## Q7. Provider capabilities

[Philosophy](level-1-philosophy.md#q7-how-can-a-pluggable-storage-abstraction-remain-honest-about-backend-guarantees) · [Code lab](level-3-code-labs.md#q7-capability-gate) · [Provider API](https://github.com/feast-dev/feast/blob/2dfb9e6d1a37719fd11028d916094050f1cdd552/sdk/python/feast/infra/provider.py)

Define a portable core for retrieval and writes, then declare capabilities such as created-time filtering, timestamp-conditional upsert, vector search, transactions, streaming ingestion, or online materialization. Validate a repository against its selected providers before deployment. Conformance suites test portable semantics; provider-specific suites test advertised extensions.

**Invariant:** orchestration invokes a capability only after the provider declares and tests it; fallback behavior is explicit rather than silent.

**Follow-ups.** Capability flags can become stale if tied only to class type, so version them. Avoid catching `NotImplemented` and quietly weakening correctness. Document performance constraints as well as functional support.

## Q8. Cross-store writes

[Philosophy](level-1-philosophy.md#q8-what-should-happen-when-one-logical-feature-write-targets-two-stores) · [Code lab](level-3-code-labs.md#q8-outbox-state-machine)

Assign the logical write an idempotency key and persist an intent before invoking stores. Track `PENDING`, per-destination acknowledgements, and `COMPLETE`; retry missing destinations and reconcile aged partial states. Alternatively make one durable log authoritative and let independent consumers update offline and online stores. Feast's push modes choose destinations, but the calls do not create a cross-store transaction.

**Invariant:** acknowledged logical writes are either complete in every required destination or durably visible to repair automation. Retries do not create a different logical version.

**Follow-ups.** Decide whether immediate online availability or eventual cross-store agreement is primary. Define compensation for an invalid value. Expose partial success rather than returning an ambiguous generic error.

## Q9. Feature observability

[Philosophy](level-1-philosophy.md#q9-how-do-you-know-whether-served-features-are-fresh-and-semantically-correct) · [Code lab](level-3-code-labs.md#q9-freshness-evaluator)

Propagate feature contract version, event timestamp, materialization watermark, and source generation into metrics or sampled traces. Measure per-feature age distributions, missing/default rates, online-offline parity, late-write rejection, materialization lag, registry version skew, and request latency. Alert against feature-specific expectations rather than one global threshold.

**Invariant:** every freshness verdict compares the correct timestamp with a declared SLO and identifies the contract version that produced the value.

**Follow-ups.** High availability can coexist with stale data. Sampling needs stable entity cohorts to make parity trends comparable. Freshness alerts should distinguish no new source events from a stuck pipeline. Maintain a repair runbook for each metric.
