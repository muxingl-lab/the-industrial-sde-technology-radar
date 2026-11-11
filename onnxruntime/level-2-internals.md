# ONNX Runtime Source Study — Level 2: Internals and Interviews

[Radar home](../README.md) · [ONNX Runtime home](README.md) · [Level 1](level-1-philosophy.md) · [Level 3](level-3-code-labs.md) · [Source map](source-map.md)

Level 2 follows the control and data path far enough to explain ownership, invariants, failure, and operational trade-offs in a senior-SDE interview.

## Q1. Model contract validation

[Philosophy](level-1-philosophy.md#q1-how-can-a-runtime-reject-an-incompatible-computation-graph-before-it-reaches-hardware) · [Code lab](level-3-code-labs.md#q1-graph-contract-validator)

Model loading parses the graph, resolves operator schemas against imported operator-set versions, checks required attributes and edge types, validates acyclicity and names, and propagates shapes where inputs make them knowable. Symbolic or absent dimensions remain unresolved and become per-run checks. External tensor data receives separate path, size, and type validation before it is used as initializer storage.

**Invariant:** every edge has one producer or declared graph input, every node matches a schema version, and every statically known consumer requirement agrees with its producer. Unknown is allowed; contradiction is not.

**Interview follow-ups.** Why retain an opset version? Operator meaning can evolve, so a name alone is not a stable contract. Why not require all shapes? Dynamic batch, sequence, and image sizes are legitimate. What remains at run time? Actual feed names, types, ranks, concrete dimensions, byte sizes, provider limits, and resource admission.

## Q2. Graph transformation

[Philosophy](level-1-philosophy.md#q2-how-can-a-runtime-rewrite-a-computation-graph-without-changing-its-result) · [Code lab](level-3-code-labs.md#q2-safe-rewrite-pass) · [Transformer manager](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/optimizer/graph_transformer_mgr.cc)

Transformers run in ordered levels. Basic passes perform semantics-preserving cleanup such as constant folding and redundant-node removal. Later passes recognize larger provider-sensitive patterns and replace them with fused nodes or layouts. A pass reports whether it changed the graph. The manager can repeat passes to a bounded step count because one rewrite may expose another. Changed graphs resolve again to rebuild edges and recheck types.

**Invariant:** graph inputs and observable outputs retain their declared contract, and every introduced node has a registered schema and kernel path for the intended build. Provider assignments and layout annotations must remain consistent with the phase in which the pass runs.

**Interview follow-ups.** Pass ordering is part of behavior. A fusion reduces launches and intermediate traffic but may reduce portability. Constant folding increases artifact size in some cases. Differential tests should compare unoptimized and optimized outputs across shapes and numerical tolerances, not merely check that the graph loads.

## Q3. Execution-provider partitioning

[Philosophy](level-1-philosophy.md#q3-how-should-one-graph-be-divided-across-backends-with-different-capabilities) · [Code lab](level-3-code-labs.md#q3-capability-aware-partitioner) · [Graph partitioner](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/framework/graph_partitioner.cc)

ONNX Runtime queries execution providers in the preference order supplied by the caller. Each provider's `GetCapability` returns supported nodes or connected subgraphs. The greedy partitioner accepts claims that remain unassigned, may replace a claimed subgraph with one fused node, and registers a provider kernel or compiled function for it. The CPU provider normally runs last and covers remaining ordinary operators.

**Invariant:** each executable node has exactly one owner and kernel, while every edge crossing owners has a legal transfer path. A provider cannot claim nodes already assigned to a higher-priority provider.

**Interview follow-ups.** Greedy priority is deterministic and practical, not a globally optimal cost search. A provider may reject an operator because of type, shape, layout, dynamic-dimension, memory, or configuration limits. Count fallback nodes and boundary transfers in production. A large partition can be worse if compilation time, workspace, or transfer placement violates the operational budget.

## Q4. Data placement and I/O binding

[Philosophy](level-1-philosophy.md#q4-how-do-you-stop-device-transfers-from-erasing-accelerator-gains) · [Code lab](level-3-code-labs.md#q4-transfer-aware-placement) · [I/O binding](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/session/IOBinding.cc)

The execution plan maps each logical value to a device and memory type. Partition boundaries introduce copy operations through the data-transfer manager. Ordinary `Run` APIs can copy caller feeds into expected locations and return host outputs. I/O binding instead lets the caller supply an existing device value or request that an output be allocated in a named device memory location. Explicit synchronization methods make device completion visible to the caller.

**Invariant:** a kernel receives values in the location and memory type its provider expects. An external buffer remains alive and unmodified for the full asynchronous use interval.

**Interview follow-ups.** Binding an output location handles dynamic output sizes; binding a fixed buffer requires enough bytes. Device identity includes device type, ID, allocator, and memory kind. Measure bytes and synchronization per boundary. A transfer saved at the runtime boundary may simply move responsibility to the application.

## Q5. Lifetime-based memory reuse

[Philosophy](level-1-philosophy.md#q5-how-can-intermediate-tensors-share-memory-without-overwriting-live-values) · [Code lab](level-3-code-labs.md#q5-liveness-buffer-planner) · [Allocation planner](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/framework/allocation_planner.cc)

Initialization assigns every value an allocation kind: external, persistent, allocate, reuse, share, or not allocated. The planner uses producer/consumer order, last use, device location, alias rules, and size information to create allocation and release actions. When concrete shapes were unknown, the first compatible run can trace actual allocations into a memory pattern. Session state caches that pattern under an input-shape signature for later runs.

**Invariant:** two values share storage only if their physical lifetimes do not overlap and the block satisfies both values' device, type, alignment, and size constraints. Persistent initializers and external outputs are not reclaimed as ordinary temporaries.

**Interview follow-ups.** Dynamic shapes can create several cached patterns or miss reuse. Shape equality alone may not capture every provider constraint, so the runtime controls eligibility. In-place reuse needs an operator contract proving the input is dead and aliasing is safe. Logical last use must be extended through asynchronous stream completion.

## Q6. Arena allocation

[Philosophy](level-1-philosophy.md#q6-when-does-an-arena-allocator-help-and-when-does-it-hide-memory-debt) · [Code lab](level-3-code-labs.md#q6-coalescing-arena) · [BFC arena](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/framework/bfc_arena.cc)

The best-fit-with-coalescing arena requests regions from an underlying allocator, divides them into chunks, and indexes free chunks by size bins. Allocation chooses a suitable free chunk, splits meaningful excess, and marks the remainder live. Freeing coalesces adjacent free chunks. An extend strategy and memory limit govern growth; shrinkage can return wholly free regions.

**Invariant:** chunks cover each owned region without overlap, adjacent free chunks eventually coalesce, and total reserved bytes never exceed the configured limit. Stream-aware arenas cannot recycle a chunk until the device stream has completed its use.

**Interview follow-ups.** Internal fragmentation is unused space inside live chunks; external fragmentation is free space that cannot satisfy a request. Arena reuse lowers allocator cost but may raise RSS. Track live, requested, reserved, maximum, fragmentation, extension, and allocation-failure metrics. Shared environment allocators improve cross-session reuse but enlarge the ownership and isolation boundary.

## Q7. Threading and oversubscription

[Philosophy](level-1-philosophy.md#q7-how-should-a-runtime-use-parallelism-without-multiplying-runnable-threads) · [Code lab](level-3-code-labs.md#q7-parallelism-budget) · [Threading notes](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/docs/NotesOnThreading.md)

Intra-op parallelism divides one kernel's loop. Inter-op parallelism schedules independent graph nodes. Sessions can own pools or use global environment pools. Operators call centralized helpers such as `TryParallelFor`, which decide whether work is large enough and whether a pool exists. Parallel sections amortize repeated loop-entry cost. Sequential graph execution often pairs with intra-op kernel parallelism; parallel graph execution introduces inter-op work as well.

**Invariant:** one configured process budget bounds runnable runtime workers, and nested parallel regions do not each assume exclusive ownership of all cores.

**Interview follow-ups.** Size pools for the product of concurrent runs and per-run parallelism. CPU affinity, NUMA locality, spin behavior, OpenMP/BLAS libraries, and memory bandwidth can dominate thread count. Benchmark throughput and P99 under real concurrency. A single-request latency optimum is rarely the fleet throughput optimum.

## Q8. Asynchronous execution

[Philosophy](level-1-philosophy.md#q8-how-should-dependencies-remain-correct-when-device-work-finishes-asynchronously) · [Code lab](level-3-code-labs.md#q8-event-fenced-scheduler) · [Sequential executor](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/framework/sequential_executor.cc)

The allocation plan groups nodes into logical streams and adds trigger, barrier, wait, and notification actions around cross-stream dependencies. A kernel launch runs with provider stream context. Independent streams may advance, while a consumer waits for the event that proves its producer complete. Release actions occur only when logical use and device completion allow reuse. Run termination is checked at dispatch boundaries; provider work already launched may still need to finish safely.

**Invariant:** every consumer observes a happens-before edge from the completion of each producer, and no buffer is freed or reused before all device users complete.

**Interview follow-ups.** A host mutex does not order GPU work. Synchronizing the whole device is correct but forfeits overlap. Errors must preserve cleanup and unblock dependents. Concurrent `Run` support can be provider-specific, especially with graph capture or stream-scoped allocators.

## Q9. Quantization contract

[Philosophy](level-1-philosophy.md#q9-when-is-reduced-numerical-precision-an-acceptable-execution-plan) · [Code lab](level-3-code-labs.md#q9-calibration-and-quality-gate) · [Quantization tools](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/python/tools/quantization/README.md)

Choose a target provider and quantized operator form first. Static quantization gathers representative activation ranges; dynamic quantization computes some parameters during inference; weight-only forms compress selected weights. QDQ graphs make quantize/dequantize boundaries explicit, while QOperator graphs encode quantized operations directly. Exclude sensitive nodes or use per-channel parameters where the accuracy-cost trade merits them.

**Invariant:** scale, zero point, axis, signedness, and tensor type agree at every quantized boundary, and the deployed provider has kernels for the resulting graph. Promotion or fallback must not silently remove the expected speedup.

**Interview follow-ups.** Compare against the full-precision model with task metrics and cohort slices. Inspect activation differences to localize loss. File size is not runtime memory, and integer arithmetic is not automatically faster. Include conversion nodes, provider partitioning, latency, throughput, and calibration drift in the decision.

## Q10. Session preparation and publication

[Philosophy](level-1-philosophy.md#q10-how-should-a-service-keep-model-preparation-off-the-first-live-request) · [Code lab](level-3-code-labs.md#q10-prepared-session-generation) · [Session initialization](https://github.com/microsoft/onnxruntime/blob/6af1a932e2286d5c58166085d24c68783033edee/onnxruntime/core/session/inference_session.cc)

Separate portable build work from host activation. A build job validates and optimizes the graph, optionally emits ORT format or provider context, records runtime/provider versions and checksums, and runs numerical tests. Each host loads the artifact, creates providers and allocators, compiles anything hardware-specific, prepackages weights, transfers initializers, warms representative shapes, and reports ready. The serving process then swaps one generation pointer and drains the old session.

**Invariant:** one request uses one fully initialized generation whose model, transforms, provider configuration, custom operators, hardware contract, and external weights share one identity.

**Interview follow-ups.** Peak memory includes old and new sessions during rollout. Parallel prepacking and pinned double-buffer loading reduce initialization time but consume CPU, I/O, pinned host memory, and device bandwidth. A checksum catches corruption, not semantic incompatibility. Retain the last known-good generation and publish readiness only after warmup and accuracy smoke tests.
