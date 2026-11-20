# Apache Flink Technology Radar

[Radar home](../README.md) · [Source map](source-map.md)

Source baseline: [Apache Flink](https://github.com/apache/flink) `release-2.3.0`, commit [`c0f8d1a1e09f209885a88f9c19ceb9d9e9870283`](https://github.com/apache/flink/tree/c0f8d1a1e09f209885a88f9c19ceb9d9e9870283).

## Reading paths

- [Level 1 — Philosophy and problem recognition](level-1-philosophy.md)
- [Level 2 — Internals, workflows, and interview follow-ups](level-2-internals.md)
- [Level 3 — Code labs and handwritten implementations](level-3-code-labs.md)

## Core problem families

1. Derive useful progress from out-of-order event timestamps
2. Bound time-indexed state and define late-data behavior
3. Partition mutable state without remote access on every record
4. Take a distributed snapshot while records continue to flow
5. Coordinate checkpointed computation with external side effects
6. Propagate overload through bounded network buffers
7. Mix data and control work without concurrent state mutation
8. Recover a distributed dataflow without inventing or losing progress
9. Redistribute state when parallelism changes
10. Choose a state representation and durable checkpoint strategy
11. Upgrade stateful code without losing the identity or meaning of state

Flink is a distributed stateful dataflow runtime. Connectors, SQL, and APIs are important, but this volume studies the runtime contracts beneath them: time, state ownership, flow control, snapshots, recovery, and evolution.
