# ONNX Runtime Technology Radar

[Radar home](../README.md) · [Source map](source-map.md)

Source baseline: [ONNX Runtime](https://github.com/microsoft/onnxruntime) `v1.31.1`, commit `6af1a932e2286d5c58166085d24c68783033edee`.

## Reading paths

- [Level 1 — Philosophy and problem recognition](level-1-philosophy.md)
- [Level 2 — Internals, workflows, and interview follow-ups](level-2-internals.md)
- [Level 3 — Code labs and handwritten implementations](level-3-code-labs.md)

## Core problem families

1. Validate a portable computation graph before execution
2. Rewrite graphs without changing their contract
3. Partition work across heterogeneous execution backends
4. Make data placement and device transfers explicit
5. Reuse intermediate memory from tensor lifetimes
6. Amortize allocation without hiding retained memory
7. Control nested parallelism and oversubscription
8. Preserve dependencies across asynchronous device streams
9. Trade numerical precision for cost under an accuracy contract
10. Move compilation and preparation off the request path

ONNX Runtime is an inference runtime, not a model server. It prepares and executes a model inside a session; admission control, request batching, model rollout, and fleet-level rollback belong to the surrounding service.
