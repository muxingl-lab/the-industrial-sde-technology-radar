# Memory Indirection Across Serving and Execution Engines

[Comparisons](README.md) · [vLLM question](../../vllm/level-1-philosophy.md#q1-how-can-per-request-memory-grow-without-reserving-its-maximum-size) · [SGLang question](../../sglang/level-1-philosophy.md#q9-how-should-logical-token-positions-map-to-reusable-physical-memory-slots) · [ONNX Runtime question](../../onnxruntime/level-1-philosophy.md#q5-how-can-intermediate-tensors-share-memory-without-overwriting-live-values)

## Common problem

Logical values need stable identities, while physical memory is fixed, fragmented, and frequently reused. All three systems insert a mapping layer so storage can change without changing the logical contract.

## Different unit of reasoning

| Dimension | vLLM | SGLang | ONNX Runtime |
|---|---|---|---|
| Logical unit | Request token positions | Request/token pool positions | Intermediate tensor values |
| Physical unit | Fixed-size KV blocks | Pool slots | Planned or shape-keyed memory blocks |
| Lifetime owner | Request scheduler and cache manager | Scheduler and memory pools | Session plan plus per-run execution frame |
| Reuse boundary | Block reference count reaches zero | Slot is removed from every live mapping | Last consumer and asynchronous completion fence |
| Main waste | Block-internal fragmentation | Mapping metadata and pool fragmentation | Peak overlap, dynamic shapes, and arena fragmentation |

The difference is fundamental to lifetime. vLLM and SGLang retain state across autoregressive scheduling turns, so request ownership and sharing drive reclamation. ONNX Runtime usually reuses temporary tensors within one graph run, so static consumer liveness and device completion drive reclamation. The abstraction is shared; the proof that storage is free is not.

## Shared invariant

No live physical region may have an unintended owner. Allocation failure must roll back every partial mapping. Shared state must remain allocated until the last reference leaves.
