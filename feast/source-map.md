# Feast Source Map

[Feast home](README.md) · [Level 1](level-1-philosophy.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

This volume was audited against Feast `v0.67.0` at commit `2dfb9e6d1a37719fd11028d916094050f1cdd552`.

| Concern | Primary source | What to inspect |
|---|---|---|
| Orchestration | [`feature_store.py`](https://github.com/feast-dev/feast/blob/2dfb9e6d1a37719fd11028d916094050f1cdd552/sdk/python/feast/feature_store.py) | `apply`, historical retrieval, online retrieval, materialization, and push |
| Registry contract | [`base_registry.py`](https://github.com/feast-dev/feast/blob/2dfb9e6d1a37719fd11028d916094050f1cdd552/sdk/python/feast/infra/registry/base_registry.py) | Metadata operations and abstraction boundary |
| Registry caching | [`caching_registry.py`](https://github.com/feast-dev/feast/blob/2dfb9e6d1a37719fd11028d916094050f1cdd552/sdk/python/feast/infra/registry/caching_registry.py) | Cache TTL, refresh, and stale metadata window |
| Point-in-time helpers | [`offline_utils.py`](https://github.com/feast-dev/feast/blob/2dfb9e6d1a37719fd11028d916094050f1cdd552/sdk/python/feast/infra/offline_stores/offline_utils.py) | Entity timestamps, TTL, created-time filtering, and validation |
| Provider boundary | [`provider.py`](https://github.com/feast-dev/feast/blob/2dfb9e6d1a37719fd11028d916094050f1cdd552/sdk/python/feast/infra/provider.py) | Infrastructure and store-dependent capabilities |
| Online-store API | [`online_store.py`](https://github.com/feast-dev/feast/blob/2dfb9e6d1a37719fd11028d916094050f1cdd552/sdk/python/feast/infra/online_stores/online_store.py) | Read/write semantics promised by the interface |
| Redis backend | [`redis.py`](https://github.com/feast-dev/feast/blob/2dfb9e6d1a37719fd11028d916094050f1cdd552/sdk/python/feast/infra/online_stores/redis.py) | Timestamp-guarded writes and performance trade-offs |
| Feature server | [`feature_server.py`](https://github.com/feast-dev/feast/blob/2dfb9e6d1a37719fd11028d916094050f1cdd552/sdk/python/feast/feature_server.py) | Request boundary and online serving path |

## Boundary decisions

- Point-in-time correctness uses an entity-row event timestamp and feature-view TTL. Created-time filtering exists but is optional and backend-dependent.
- Materialization moves values from offline storage into an online store and records progress; rows plus progress are not one universal atomic transaction.
- `push` to online and offline destinations invokes distinct writes. Treat it as a recoverable dual-write workflow, not atomic fan-out.
- The Redis online store can reject older updates using timestamps. A throughput-oriented option can skip that protection; the base interface does not guarantee identical conflict handling across all stores.
- Registry caching trades metadata freshness for lower read cost. `apply` coordinates metadata and infrastructure, but does not make the entire rollout one atomic commit.

## Excluded claims

This volume does not claim that Feast automatically guarantees training-serving consistency, that all providers implement equal semantics, or that registry state alone proves infrastructure readiness. Those properties require explicit timestamp contracts, transformation parity, backend capability checks, and operational evidence.
