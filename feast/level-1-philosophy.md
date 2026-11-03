# Feast Source Study — Level 1: Philosophy

[Radar home](../README.md) · [Feast home](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

Level 1 starts with ordinary data systems: requests arrive now, facts happened earlier, offline jobs produce tables, and online services need low-latency values. The hard part is preserving meaning while data moves between those contexts.

## Q1. How can training reconstruct only what was knowable at each historical decision time?

**Starting point.** A model is trained from historical examples. Each row represents a decision made at an entity timestamp, while feature tables contain many later observations for that entity.

**What breaks.** Joining each entity to the latest feature value today leaks future information into old examples. The offline metric improves, but production can never possess that information at decision time.

**The question.** How should every entity row select the newest eligible feature event without crossing its own time boundary or retention window?

**Philosophy:** historical retrieval is an as-of query, not an ordinary key join. Time is part of the key and future leakage is a correctness bug.

**Feast example:** point-in-time joins use entity keys, event timestamps, and feature-view TTLs.

**Warning:** event time, creation time, ingestion time, and request time are different facts; collapsing them hides late data and backfills.

[Go deeper](level-2-internals.md#q1-point-in-time-retrieval) · [Implement it](level-3-code-labs.md#q1-point-in-time-join)

## Q2. How can one feature retain the same meaning in training and online serving?

**Starting point.** An offline pipeline computes a value for millions of training rows. An online request fetches one entity in milliseconds. They may run different languages, stores, and refresh schedules.

**What breaks.** Matching column names do not prove matching semantics. Different default values, windows, entity keys, transforms, or versions create training-serving skew.

**The question.** What contract identifies a feature and makes both paths demonstrably equivalent?

**Philosophy:** reuse a versioned definition and test values at the boundary. Configuration reuse helps, but evidence of parity closes the loop.

**Feast example:** entities, feature views, schemas, sources, TTLs, and services are registered metadata used by historical and online retrieval.

**Warning:** a shared registry cannot repair a transform implemented differently outside it.

[Go deeper](level-2-internals.md#q2-feature-contract) · [Implement it](level-3-code-labs.md#q2-contract-fingerprint)

## Q3. How should a large offline-to-online materialization survive interruption?

**Starting point.** An online store must be populated from an offline history. The time range may contain billions of rows, and periodic refreshes must advance while serving continues.

**What breaks.** One giant job is expensive to retry. Advancing the progress marker before all writes finish creates a hole; retrying non-idempotent writes creates corruption.

**The question.** How should the work be partitioned, retried, and recorded so an interruption neither skips nor invents state?

**Philosophy:** make backfill progress monotonic, chunks replayable, and the checkpoint subordinate to completed writes.

**Feast example:** full and incremental materialization query time intervals and persist materialization progress in the registry.

**Warning:** a recorded interval boundary is not proof that every backend write committed atomically with it.

[Go deeper](level-2-internals.md#q3-materialization) · [Implement it](level-3-code-labs.md#q3-resumable-materializer)

## Q4. How should an online store handle an older update that arrives after a newer one?

**Starting point.** Streams retry, partitions lag, and backfills overlap live traffic. Two updates for one entity can arrive in the opposite order from their event timestamps.

**What breaks.** Blind last-arrival-wins storage allows an old value to replace fresh state. Adding a read-before-write comparison introduces races unless the store makes it atomic.

**The question.** Which version orders updates, and where is the compare-and-set enforced?

**Philosophy:** when arrival order is unreliable, make freshness explicit and reject stale writes at the authoritative storage boundary.

**Feast example:** the Redis online store normally compares timestamps, with an optional faster path that skips this deduplication.

**Warning:** the online-store abstraction does not guarantee identical conflict semantics for every provider.

[Go deeper](level-2-internals.md#q4-out-of-order-updates) · [Implement it](level-3-code-labs.md#q4-timestamp-guarded-upsert)

## Q5. Where should a feature transformation run?

**Starting point.** A feature may be computed in a warehouse, during materialization, from request fields, or inside the serving process. Each location has different data access and latency.

**What breaks.** Duplicating logic creates skew. Putting expensive transforms on the request path breaks latency. Precomputing request-dependent values may be impossible.

**The question.** Which inputs are available at each stage, and what makes offline and online computation equivalent?

**Philosophy:** place stable, reusable work off-path; keep request-dependent work close to serving; version and parity-test every shared transform.

**Feast example:** feature views and on-demand feature views separate stored values from request-time transformations.

**Warning:** “same code” is insufficient if dependencies, null handling, or input timestamps differ.

[Go deeper](level-2-internals.md#q5-transformation-placement) · [Implement it](level-3-code-labs.md#q5-parity-harness)

## Q6. How should metadata and infrastructure change without creating a split-brain schema?

**Starting point.** A feature definition change can affect registry metadata, offline queries, online tables, feature servers, and clients. They cannot all change in one process instruction.

**What breaks.** Publishing metadata before infrastructure is ready sends readers to missing state. Changing infrastructure first can leave unused or incompatible resources. Cached registries extend the mixed-version window.

**The question.** What plan, compatibility rule, and rollout state make a multi-component change safe?

**Philosophy:** treat configuration as a versioned control-plane rollout with explicit readiness, compatibility, and rollback—not as one atomic file write.

**Feast example:** `apply` coordinates registry objects and provider infrastructure; registry caching introduces a bounded staleness window.

**Warning:** orchestration order does not provide a distributed transaction.

[Go deeper](level-2-internals.md#q6-metadata-rollout) · [Implement it](level-3-code-labs.md#q6-plan-and-apply)

## Q7. How can a pluggable storage abstraction remain honest about backend guarantees?

**Starting point.** Teams want the same feature API over Redis, databases, warehouses, and cloud services. Their transactions, timestamp comparisons, batch writes, and failure modes differ.

**What breaks.** A lowest-common-denominator interface hides useful guarantees; an overly strong interface promises behavior some providers cannot implement.

**The question.** Which semantics are portable, which are declared capabilities, and which remain application responsibilities?

**Philosophy:** abstract the workflow, but expose capability and consistency boundaries. Portability must not erase correctness differences.

**Feast example:** provider, offline-store, online-store, and registry interfaces delegate concrete behavior to plugins.

**Warning:** successful conformance tests for method shape do not prove equivalent operational semantics.

[Go deeper](level-2-internals.md#q7-provider-capabilities) · [Implement it](level-3-code-labs.md#q7-capability-gate)

## Q8. What should happen when one logical feature write targets two stores?

**Starting point.** A pushed value may need an online store for immediate inference and an offline store for future training. These systems do not share a transaction manager.

**What breaks.** The first write may commit and the second fail. Blind retries may duplicate side effects. Reporting success after only one write makes later training disagree with serving.

**The question.** Where does atomicity end, and how will the system detect, retry, or reconcile partial success?

**Philosophy:** model cross-system writes as a state machine with idempotency, durable intent, and reconciliation. Do not imply atomicity the stores cannot provide.

**Feast example:** pushing to online and offline destinations invokes separate backend writes.

**Warning:** sequential API calls are not a transaction, even when one SDK method starts them.

[Go deeper](level-2-internals.md#q8-cross-store-writes) · [Implement it](level-3-code-labs.md#q8-outbox-state-machine)

## Q9. How do you know whether served features are fresh and semantically correct?

**Starting point.** A feature server can return HTTP 200 while serving stale values, missing entities, outdated definitions, or a partially materialized interval.

**What breaks.** Infrastructure uptime metrics observe availability but not feature meaning. A global freshness average hides one broken feature or entity cohort.

**The question.** Which timestamps, versions, null rates, parity samples, and materialization states must travel through the system and become alerts?

**Philosophy:** observe semantic debt, not only machine health. Freshness and correctness require data-plane evidence tied to a feature version.

**Feast example:** registry metadata and materialization state provide context, while production systems must add end-to-end freshness and parity measurements.

**Warning:** wall-clock age alone cannot distinguish an intentionally slow feature from a failed pipeline.

[Go deeper](level-2-internals.md#q9-feature-observability) · [Implement it](level-3-code-labs.md#q9-freshness-evaluator)
