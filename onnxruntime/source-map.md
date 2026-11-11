# ONNX Runtime Source Map

[ONNX Runtime home](README.md) · [Level 1](level-1-philosophy.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

This volume was audited against ONNX Runtime `v1.31.1` at commit `6af1a932e2286d5c58166085d24c68783033edee`. The links below pin implementation evidence to that revision.

| Concern | Primary source | What to inspect |
|---|---|---|
| Session lifecycle | [`inference_session.cc`](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/session/inference_session.cc) | Model loading, graph transformation, initialization, `Run`, cancellation, and profiling |
| Graph rewriting | [`graph_transformer_mgr.cc`](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/optimizer/graph_transformer_mgr.cc) | Ordered transformer levels, repeated passes, and graph resolution |
| Backend partitioning | [`graph_partitioner.cc`](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/framework/graph_partitioner.cc) | Provider priority, `GetCapability`, fused subgraphs, compilation, and CPU fallback |
| Execution plan | [`allocation_planner.cc`](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/framework/allocation_planner.cc) | Value locations, lifetimes, reuse, release actions, and logical streams |
| Runtime frame | [`execution_frame.cc`](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/framework/execution_frame.cc) | Per-run values, allocation, dynamic shapes, and memory-pattern generation |
| Cached session state | [`session_state.cc`](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/framework/session_state.cc) | Kernels, execution plans, allocators, streams, and shape-keyed memory patterns |
| Device-bound inputs and outputs | [`IOBinding.cc`](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/session/IOBinding.cc) | Binding values or memory locations and synchronizing device data |
| Arena allocation | [`bfc_arena.cc`](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/framework/bfc_arena.cc) | Region extension, bins, splitting, coalescing, limits, and shrinkage |
| Operator execution | [`sequential_executor.cc`](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/framework/sequential_executor.cc) | Kernel dispatch, dependency release, stream context, termination, and errors |
| Threading contract | [`NotesOnThreading.md`](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/docs/NotesOnThreading.md) | Intra-op versus inter-op pools and centralized parallel-loop helpers |
| Quantization pipeline | [`python/tools/quantization/README.md`](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/python/tools/quantization/README.md) | Calibration, QDQ/QOperator forms, debugging, and provider support |
| Load-time work | [`Model_Loading_Performance.md`](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/docs/Model_Loading_Performance.md) | Weight prepacking, external initializers, pinned buffers, and bounded staging |

## End-to-end path

1. Load and resolve the model graph against operator schemas and types.
2. Apply graph rewrites at ordered optimization levels.
3. Ask execution providers, in configured priority order, which nodes or subgraphs they can own.
4. Compile fused provider subgraphs and assign remaining work, normally to CPU.
5. Create kernels, a value-location map, an allocation plan, and logical device streams.
6. For each `Run`, bind feeds and fetches, allocate an execution frame, dispatch ready kernels, synchronize required transfers, and release values at their last use.
7. Cache a memory pattern when a compatible input-shape signature makes the observed allocation layout reusable.

## Boundary decisions

- Provider order changes partition ownership. “GPU enabled” does not mean every node runs on a GPU.
- A supported operator can still cause expensive boundary copies when adjacent nodes land on different devices.
- Memory reuse is valid only when lifetimes do not overlap and the device, allocator, type, size, and alias rules remain compatible.
- Arenas reduce allocation overhead but can retain regions after a request completes. Allocated bytes, reserved bytes, and process RSS are different signals.
- Quantization is useful only when the target provider has suitable kernels and measured model accuracy remains inside its contract.
- Session initialization may transform, partition, compile, prepack, and copy weights. A production service must keep that work away from the first live request.
