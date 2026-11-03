# Roadmap

[Radar home](README.md) · [Problem library](library/README.md) · [Contributing](CONTRIBUTING.md)

The next volume should earn its place by adding problem-solving coverage, not by adding another recognizable name. This roadmap favors systems whose source code teaches a major family of production decisions that the current Redis, Valkey, vLLM, and SGLang volumes do not yet cover.

This is a reading queue, not a delivery promise. A folder is created only when source study begins and a release and commit can be pinned.

## Recommended next three

### 1. PostgreSQL — transactions and database internals

PostgreSQL should be next. It adds the broadest missing foundation for a backend engineer.

**Problem families to extract**

- How can readers observe stable data while writers continue to modify it?
- Why does multiversion concurrency control create dead tuples, and how should vacuum reclaim them?
- What must reach durable storage before a transaction may acknowledge success?
- How do checkpoints trade recovery time against foreground I/O?
- How does a planner choose among scans, joins, and indexes when its estimates are uncertain?
- How do buffer management, page layout, and locality change an algorithm's real cost?
- Where do transaction isolation levels prevent anomalies, and where must applications still retry?

**Expected cross-links:** Redis persistence and background reclamation; RocksDB write-ahead logging; FoundationDB concurrency control; bounded background work.

**Primary starting points:** [PostgreSQL source](https://github.com/postgres/postgres), [concurrency control](https://www.postgresql.org/docs/current/mvcc.html), and [write-ahead logging](https://www.postgresql.org/docs/current/wal-intro.html).

### 2. Apache Kafka — ordered logs and coordinated consumers

Kafka turns a familiar queue-shaped problem into a study of ordering, retention, replication, and distributed ownership.

**Problem families to extract**

- How should a stream be partitioned when global order is too expensive?
- How can sequential disk I/O outperform designs built around many random updates?
- What does a producer acknowledgment actually guarantee under broker failure?
- How do consumer groups transfer partition ownership without concurrent processing?
- How should offsets, retries, and side effects combine to produce useful delivery semantics?
- Why can retention decouple producers from consumers, and when does lag become unrecoverable?
- How do replication and leader epochs prevent stale replicas from acting as authorities?

**Expected cross-links:** Redis replication history; ownership and fencing; overload and backpressure; PostgreSQL WAL; Temporal event history.

**Primary starting points:** [Kafka source](https://github.com/apache/kafka) and the [official design documentation](https://kafka.apache.org/documentation/).

### 3. Kubernetes — reconciliation and control planes

Kubernetes adds a different architecture family: systems that repeatedly reconcile observed state toward declared intent.

**Problem families to extract**

- Why is a retryable reconciliation loop safer than a one-shot imperative workflow?
- How should `spec`, `status`, identity, and generation separate intent from observation?
- How do watches avoid polling without making missed events a correctness failure?
- How do controllers remain idempotent when work is duplicated or restarted?
- How should a scheduler separate filtering, scoring, reservation, and binding?
- Why do finalizers turn deletion into a protocol rather than an instant state change?
- How do leases, leader election, and resource versions fence stale actors?

**Expected cross-links:** ownership and stale-completion fencing; Redis cluster decisions; bounded work queues; overload control; etcd watches and leases.

**Primary starting points:** [Kubernetes source](https://github.com/kubernetes/kubernetes), [objects and desired state](https://kubernetes.io/docs/concepts/overview/working-with-objects/), and [controllers](https://kubernetes.io/docs/concepts/architecture/controller/).

## Second wave: mechanism specialists

These systems deepen one important mechanism after the first wave establishes its surrounding context.

| Priority | System | What it uniquely teaches | Likely comparison patterns |
|---|---|---|---|
| 4 | [RocksDB](https://github.com/facebook/rocksdb) | LSM trees, memtables, SSTables, Bloom filters, compaction debt, write and space amplification | PostgreSQL WAL and cleanup; Redis representations; bounded background work |
| 5 | [Envoy](https://github.com/envoyproxy/envoy) | Event-driven proxying, connection pools, retries, circuit breaking, load balancing, dynamic xDS configuration | Backpressure; ownership; locality-aware routing; stale configuration |
| 6 | [Temporal](https://github.com/temporalio/temporal) | Durable execution, event-history replay, deterministic workflow code, activity retries, versioning | Kafka logs; idempotency; cancellation; stale completion; Redis atomicity boundaries |
| 7 | [ClickHouse](https://github.com/ClickHouse/ClickHouse) | Columnar layout, vectorized execution, sparse indexing, immutable parts, background merges | RocksDB compaction; bounded work; physical representation; accelerator batching |
| 8 | [etcd](https://github.com/etcd-io/etcd) | Raft, linearizable metadata, revisions, watches, leases, and compaction | Kubernetes control planes; Redis failure decisions; Kafka epochs and logs |
| 9 | [FAISS](https://github.com/facebookresearch/faiss) | Exact and approximate vector search, inverted files, graph indexes, product quantization, and CPU/GPU execution | Approximation budgets; memory representation; batching; locality; recommendation retrieval |
| 10 | [Feast](https://github.com/feast-dev/feast) | Point-in-time training joins, offline-to-online materialization, feature metadata, freshness, and pluggable serving stores | Temporal correctness; dual writes; bounded backfills; metadata rollout; Redis serving |

The order is intentional. RocksDB exposes storage trade-offs in a compact engine. Envoy adds the network boundary every backend system eventually meets. Temporal then connects logs, retries, ownership, and application-visible side effects. FAISS follows the foundational storage and scheduling volumes because its most useful lessons come from comparing several index families under an explicit quality budget. Feast comes after the storage and streaming foundations because its central lesson is how those components preserve—or fail to preserve—one feature's meaning across time and serving paths.

### FAISS study boundary

FAISS deserves a volume because vector retrieval makes approximation an operational contract rather than an isolated algorithm choice.

**Problem families to extract**

- When is exhaustive search still the correct baseline, and how should an approximate index be evaluated against it?
- How should a system trade recall, query latency, index-build cost, and bytes per vector?
- Why does an inverted file reduce the search space, and how should the number of probed lists change under a latency budget?
- When should graph traversal, coarse quantization, product quantization, or a composite index be used?
- How do training data and distribution drift affect an index built from learned centroids or codebooks?
- Which data should remain on the CPU or GPU, and when does transfer cost erase faster computation?
- How should deletions, filtering, incremental additions, and index replacement work when the serving index is not a transactional database?

**Expected cross-links:** Redis approximation; vLLM and SGLang memory layout and GPU batching; bounded work; adaptive representation; ClickHouse vectorized execution; recommendation candidate retrieval.

**Primary starting points:** [FAISS source and overview](https://github.com/facebookresearch/faiss), the [index selection reference](https://github.com/facebookresearch/faiss/wiki/Faiss-indexes), Meta's [GPU index architecture note](https://engineering.fb.com/2025/05/08/data-infrastructure/accelerating-gpu-indexes-in-faiss-with-nvidia-cuvs/), and the completed [candidate study](references/candidate-studies/faiss.md).

### Feast study boundary

Feast deserves a volume because a production feature is not just a column. It is a time-dependent contract that must retain its meaning across historical training, materialization, streaming updates, and low-latency serving.

**Problem families to extract**

- How can training reconstruct what was knowable at each historical decision time without leaking future data?
- Why must a system distinguish event time from the time a value was created or ingested?
- How can one feature definition drive both offline retrieval and online serving without hiding backend differences?
- How should materialization record progress and recover when only part of an interval reaches the online store?
- What should happen when an older feature update arrives after a newer value has already been served?
- Where should transformations run when precomputation improves latency but on-demand work improves freshness?
- How should metadata definitions and physical storage roll out when they cannot commit together?
- How should a push operation recover when its online and offline writes do not succeed together?

**Expected cross-links:** Redis and Valkey online serving; bounded work; ownership and atomicity boundaries; Kafka event transport; PostgreSQL temporal visibility; Kubernetes reconciliation; FAISS-backed vector retrieval.

**Primary starting points:** [Feast source](https://github.com/feast-dev/feast), the [architecture overview](https://docs.feast.dev/getting-started/architecture/overview), and the completed [candidate study](references/candidate-studies/feast.md).

## Advanced comparative volumes

These are valuable after the core patterns exist. They are harder to teach well because each combines several mechanisms that deserve earlier reference chapters.

| System | Why defer it | Distinctive payoff |
|---|---|---|
| [FoundationDB](https://github.com/apple/foundationdb) | Its transaction path, role-specialized architecture, recovery, and simulation framework require a strong distributed-systems base | Strict serializable transactions, decoupled system roles, rate control, deterministic simulation testing |
| [DuckDB](https://github.com/duckdb/duckdb) | Its best comparisons become clearer after PostgreSQL and ClickHouse establish row, column, and distributed execution trade-offs | In-process analytics, vectorized pipelines, morsel-driven parallelism, compact execution formats |
| [Ray](https://github.com/ray-project/ray) | Distributed task execution overlaps with schedulers, object stores, and failure recovery; the boundaries should be established first | Futures, distributed ownership, lineage reconstruction, actor lifecycle, scheduling under heterogeneous resources |

## Coverage map

The roadmap should produce a balanced radar rather than a database-heavy bookshelf.

| Architecture family | Current anchor | Planned anchor |
|---|---|---|
| In-memory serving | Redis, Valkey | — |
| AI inference scheduling | vLLM, SGLang | — |
| Transactional database | — | PostgreSQL, then FoundationDB |
| Durable log and streaming | — | Kafka |
| Declarative control plane | — | Kubernetes, then etcd |
| Embedded storage engine | — | RocksDB |
| Network data plane | — | Envoy |
| Durable workflow runtime | — | Temporal |
| Analytical execution | — | ClickHouse, then DuckDB |
| Vector similarity search | — | FAISS |
| ML feature platform | — | Feast |
| Distributed task runtime | — | Ray |

## Admission rule for future candidates

Before adding another name, answer five questions:

1. Which important production failure can this system explain better than every current volume?
2. Which transferable mechanism will a reader be able to recognize elsewhere?
3. Which existing pattern will gain a meaningful comparison rather than a repeated implementation?
4. Is the active source path small enough to trace and test at a pinned revision?
5. Can the volume support all three levels without turning Level 1 into product vocabulary or Level 3 into copied source?

If the answers are weak, keep the system in the candidate queue. Popularity alone is not coverage.
