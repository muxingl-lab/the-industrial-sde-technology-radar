# Source Study Method

## Establish provenance

Record the upstream repository, release tag, exact commit, and study date. A moving default branch is useful for discovery but is not a stable citation target.

## Build the system map

Locate these paths before drafting questions:

1. public request/API entry;
2. configuration and feature selection;
3. central scheduler or event loop;
4. request/job state machine;
5. memory/cache allocator and ownership metadata;
6. execution workers and device/runtime boundary;
7. distributed coordinator and transport;
8. persistence or recovery path, if present;
9. cancellation, timeout, overload, and cleanup paths;
10. metrics, tracing, logs, and debug state.

Follow at least one representative request end to end. Search comments and tests as well as class names: tests often reveal invariants more clearly than abstractions do.

## Extract durable lessons

For each mechanism, ask:

- What workload pathology forced this design?
- What is scarce?
- What invariant cannot be violated?
- What is deliberately approximate, delayed, duplicated, or moved off-path?
- What new intermediate state does the solution create?
- What happens under cancellation, overload, crash, partition, or stale metadata?
- Which metrics distinguish healthy trade-offs from hidden debt?
- Where else does the same pattern apply?

Reject a candidate question if its only useful answer is a symbol name or configuration flag.

## Evidence discipline

- Prefer source for implementation claims and official docs/papers for intended architecture.
- Confirm that documented concepts still map to the pinned implementation.
- Use tests to validate edge semantics.
- Avoid benchmark claims unless the workload, hardware, version, and metric are stated.
- Distinguish an architectural inference from an explicit upstream claim.
