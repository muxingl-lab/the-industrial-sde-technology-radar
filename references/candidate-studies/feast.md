# Feast Candidate Study

[Roadmap](../../ROADMAP.md) · [Problem library](../../library/README.md) · [Pattern registry](../../library/patterns.json)

## Provenance

- Upstream: [`feast-dev/feast`](https://github.com/feast-dev/feast)
- Inspected revision: [`72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9`](https://github.com/feast-dev/feast/tree/72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9)
- Study date: 2026-11-02
- Status: roadmap admission study, not a pinned book volume

The revision records what was inspected. A future volume must pin a released tag and recheck every provider selected for detailed treatment.

## Admission decision

Feast adds a missing architecture family: a feature platform that must make the same logical feature usable in historical training and low-latency inference. Its durable lessons are not “how to call a feature store.” They are how to define time, prevent future information from entering past examples, move values between storage tiers, and expose freshness and dual-write boundaries honestly.

Feast passes the roadmap admission test. Its Python orchestration path, registry, provider interfaces, point-in-time joins, online stores, materialization tests, and feature server provide concrete implementation evidence. The volume must keep backend-dependent semantics visible; the abstraction does not make every offline or online store behave identically.

## Verified source map

| Concern | Active evidence | Engineering lesson |
|---|---|---|
| Public orchestration | [`sdk/python/feast/feature_store.py`](https://github.com/feast-dev/feast/blob/72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9/sdk/python/feast/feature_store.py) | `FeatureStore` coordinates apply, historical retrieval, materialization, push, and online retrieval; it delegates storage behavior. |
| Metadata authority | [`infra/registry/base_registry.py`](https://github.com/feast-dev/feast/blob/72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9/sdk/python/feast/infra/registry/base_registry.py), [`registry.py`](https://github.com/feast-dev/feast/blob/72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9/sdk/python/feast/infra/registry/registry.py), and [`caching_registry.py`](https://github.com/feast-dev/feast/blob/72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9/sdk/python/feast/infra/registry/caching_registry.py) | Feature definitions live in a registry whose backend and cache policy affect update atomicity, visibility, and request latency. |
| Historical retrieval | [`infra/offline_stores/offline_utils.py`](https://github.com/feast-dev/feast/blob/72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9/sdk/python/feast/infra/offline_stores/offline_utils.py) | Entity keys, event timestamps, time-to-live windows, and optional created-time filtering build the point-in-time join contract. |
| Storage boundary | [`infra/provider.py`](https://github.com/feast-dev/feast/blob/72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9/sdk/python/feast/infra/provider.py) and [`online_store.py`](https://github.com/feast-dev/feast/blob/72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9/sdk/python/feast/infra/online_stores/online_store.py) | Provider and store interfaces separate orchestration from backend behavior, but consistency capabilities still vary by implementation. |
| Redis serving implementation | [`infra/online_stores/redis.py`](https://github.com/feast-dev/feast/blob/72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9/sdk/python/feast/infra/online_stores/redis.py) | The default path checks timestamps to resist older overwrites; an optional fast path skips that protection for throughput. |
| End-to-end consistency tests | [`tests/utils/e2e_test_validation.py`](https://github.com/feast-dev/feast/blob/72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9/sdk/python/tests/utils/e2e_test_validation.py) | Tests materialize an interval, compare offline and online reads, advance incremental materialization, and verify recorded intervals. |
| Point-in-time execution test | [`tests/component/spark/test_nodes.py`](https://github.com/feast-dev/feast/blob/72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9/sdk/python/tests/component/spark/test_nodes.py) | The join and dedup path selects the newest eligible feature row for each entity-time pair. |
| HTTP serving boundary | [`sdk/python/feast/feature_server.py`](https://github.com/feast-dev/feast/blob/72013d31fd0a014bfac9d4ea9f0d87a5f5a7aca9/sdk/python/feast/feature_server.py) | Serving wraps `FeatureStore`; registry refresh, materialization execution, and online reads remain separate operational paths. |

## Representative workflows

### Historical training retrieval

A caller supplies entity keys and an event timestamp for each training example. `FeatureStore.get_historical_features` resolves feature definitions through the registry and asks the offline-store provider for a retrieval job. The point-in-time query joins only feature events at or before each example time and applies each feature view's time-to-live window. When enabled and supported, created-time filtering also rejects values that describe an old event but were not known until later.

The invariant is temporal, not merely relational: a training row must not observe information from its future. Event time answers when the underlying fact happened. Created time can answer when the platform learned that fact. Conflating them can produce leakage even when entity keys and SQL joins are correct.

### Materialization and online retrieval

Materialization selects a time interval, pulls the latest eligible values from the offline store, and writes entity-keyed rows into an online store. Incremental materialization derives its next start from recorded materialization intervals. Online retrieval resolves requested feature definitions through the registry, encodes entity keys, and reads the latest stored values from the online backend.

The registry records orchestration progress, but it is not a transaction that atomically covers the offline source, every online-store write, and the progress update. A crash audit must therefore ask which rows were written, which interval was recorded, and whether replay is safe.

### Push writes

`FeatureStore.push` can target the online store, the offline store, or both. In the combined mode, the code invokes distinct write paths. This is not an atomic cross-store transaction. A producer or platform must define retry identity, partial-failure handling, and which store is authoritative when only one write succeeds.

## Ownership and consistency boundaries

| State | Authority | Important boundary |
|---|---|---|
| Feature definitions and service composition | Registry | Cached readers may observe an older registry until refresh; `apply` also updates infrastructure, so metadata and physical resources form a rollout protocol. |
| Historical values | Configured offline store | Backend-specific SQL or compute implements point-in-time semantics. Capability must be checked, not assumed from the interface. |
| Latest serving values | Configured online store | Timestamp conflict handling, atomicity, batching, and async behavior vary by backend and configuration. |
| Materialization progress | Registry metadata | A recorded interval is orchestration state, not proof of an atomic transfer across every row. |
| On-demand transformations | Request or write path, depending on configuration | Moving computation changes latency, reproducibility, and which runtime owns the transformation version. |
| Push completion | Caller plus selected store paths | `ONLINE_AND_OFFLINE` creates a dual-write failure boundary. |

## Overlap audit

| Candidate problem | Existing or planned relationship | Classification | Boundary |
|---|---|---|---|
| Serve the latest value with low latency | Redis and Valkey | Same mechanism used inside a broader contract | Redis can implement an online store, but Feast also owns feature identity, event timestamps, materialization, and historical retrieval. |
| Prevent an older write from replacing newer state | Redis ownership and atomicity questions | Same problem, backend-specific mechanism | Feast's Redis backend compares timestamps unless a throughput-oriented option disables the check; the interface alone does not guarantee this behavior everywhere. |
| Bound and resume background data movement | Existing bounded-work pattern | Same pattern, different work unit | Materialization budgets rows, partitions, or jobs across external stores rather than event-loop time or GPU tokens. |
| Keep metadata and physical resources aligned | Planned Kubernetes reconciliation | Same problem, different control loop | `apply` diffs definitions, changes registry state, and asks a provider to update infrastructure; partial failure creates rollout state. |
| Move events into online state | Planned Kafka streaming | Neighboring problem | Kafka provides ordered durable transport; Feast defines feature semantics and serving state but may rely on external stream processing. |
| Reconstruct past application state | Planned Temporal replay | Neighboring problem | Temporal replays a workflow history; Feast performs temporal joins over facts to construct training examples. |
| Preserve historical visibility | Planned PostgreSQL multiversion concurrency | Neighboring problem | MVCC gives transactions a database snapshot; Feast joins each example to domain events using event-time and optional created-time rules. |
| Retrieve vector candidates | FAISS | Optional integration, not the core pattern | Feast can use vector-capable online stores, including a FAISS backend, but feature consistency and ANN quality remain separate contracts. |

Feast should not be added to the current pattern registry until a full volume assigns stable question IDs. Likely future comparison chapters include temporal correctness, materialization and backfill, metadata rollout, and cross-store dual writes.

## Candidate question boundary

1. How can training reconstruct what was knowable at each historical decision time?
2. Why are event time, creation time, ingestion time, and request time different correctness dimensions?
3. How can one feature definition serve both historical batch retrieval and low-latency online reads without silently changing meaning?
4. How should a system materialize offline values into an online store and resume safely after partial failure?
5. What should happen when an older feature update arrives after a newer one?
6. Where should feature transformations run: before ingestion, on write, during batch retrieval, or on request?
7. How should metadata changes and physical storage changes roll out when they cannot commit as one transaction?
8. What guarantees can a pluggable storage interface promise when backends differ in atomicity, timestamp checks, and asynchronous behavior?
9. How should a push path recover when online and offline writes do not succeed together?
10. Which freshness, skew, null-rate, materialization-lag, and retrieval-latency signals reveal a broken feature pipeline before model quality drops?

## Claims deliberately excluded

- No blanket claim that Feast automatically guarantees training-serving consistency. It supplies definitions and workflows; correctness still depends on timestamps, transformations, backend capabilities, and operations.
- No claim that `ONLINE_AND_OFFLINE` push is an atomic dual write.
- No claim that created-time leakage protection is universal or enabled by default; the inspected API exposes it as an option and backends declare support.
- No claim that every online store rejects out-of-order writes in the same way.
- No attempt to treat every Feast integration as core source. A future volume should choose representative backends and state the exclusions.
