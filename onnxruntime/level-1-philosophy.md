# ONNX Runtime Source Study — Level 1: Philosophy

[Radar home](../README.md) · [ONNX Runtime home](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

Level 1 assumes that the reader understands requests, computation graphs, tensors, threads, memory, and CPU/GPU devices. It does not assume prior knowledge of ONNX Runtime.

## Q1. How can a runtime reject an incompatible computation graph before it reaches hardware?

**Starting point.** A model arrives as a directed graph. Nodes name operations. Edges carry typed, shaped values. The producer and runtime may use different library versions, and some dimensions may remain unknown until a request arrives.

**What breaks.** If validation waits until a kernel starts, a missing operator, invalid attribute, incompatible type, or impossible shape fails after the service has spent time loading weights and reserving devices. Treating the file as trusted code can also turn malformed metadata into unsafe allocation decisions.

**The question.** Which parts of the graph contract can be proved at load time, which remain runtime checks, and how should versions evolve without changing old model meaning?

**Philosophy:** validate the strongest available contract before resource acquisition. Keep unknown dimensions explicit instead of guessing, and bind operator semantics to a versioned schema.

**Think of:** bytecode verification, query analysis, API schema validation, capability negotiation.

**ONNX Runtime example:** graph resolution checks schemas, operator sets, types, edges, and inferable shapes before session execution.

**Warning:** a structurally valid graph can still exceed memory, use unsupported provider kernels, or produce unacceptable numerical results.

[Go deeper](level-2-internals.md#q1-model-contract-validation) · [Implement it](level-3-code-labs.md#q1-graph-contract-validator)

## Q2. How can a runtime rewrite a computation graph without changing its result?

**Starting point.** A portable graph describes what to compute, but often not the cheapest sequence for one machine. Constant folding can remove work. A fused kernel can replace several nodes and avoid intermediate memory traffic.

**What breaks.** Rewrites can change broadcasting, type promotion, floating-point order, output names, or provider eligibility. Applying individually valid rewrites in the wrong order can expose a graph no backend expects.

**The question.** How should the runtime order, validate, and test transformations whose purpose is speed but whose obligation is semantic equivalence?

**Philosophy:** treat optimization as a compiler pipeline. Each pass has a precondition, a bounded mutation, and a postcondition that the graph still resolves.

**Think of:** compiler intermediate-representation passes, database query rewrites, peephole optimization.

**ONNX Runtime example:** graph transformers run at ordered levels and re-resolve changed graphs; fusions create provider-ready subgraphs.

**Warning:** floating-point equivalence is often tolerance-based, not bit-for-bit equality.

[Go deeper](level-2-internals.md#q2-graph-transformation) · [Implement it](level-3-code-labs.md#q2-safe-rewrite-pass)

## Q3. How should one graph be divided across backends with different capabilities?

**Starting point.** A server may have CPU kernels for every ordinary operation, GPU kernels for a large subset, and a compiler-backed accelerator that only accepts particular connected subgraphs. A single request still expects one result.

**What breaks.** Requiring one backend to support the whole graph wastes available acceleration. Assigning each node to its locally fastest backend can create many transfers and synchronization points. Silent fallback can make a deployment “work” while missing its latency target.

**The question.** Who claims each node, how is overlap resolved, what provides complete fallback, and when is a larger supported partition worse than a smaller one?

**Philosophy:** capability is not placement. Partition under an explicit priority and whole-path cost model, then make every fallback visible.

**Think of:** federated query planning, tiered storage, heterogeneous task scheduling.

**ONNX Runtime example:** execution providers report capabilities in configured priority order; the partitioner assigns unclaimed subgraphs and normally leaves a CPU provider as the final fallback.

**Warning:** provider priority is policy. Changing the list or order can change both performance and numerical behavior.

[Go deeper](level-2-internals.md#q3-execution-provider-partitioning) · [Implement it](level-3-code-labs.md#q3-capability-aware-partitioner)

## Q4. How do you stop device transfers from erasing accelerator gains?

**Starting point.** Inputs begin in application memory. Weights may live on a CPU or accelerator. Intermediate tensors cross partition boundaries, and outputs may be consumed by another device operation instead of the host.

**What breaks.** A fast kernel surrounded by blocking copies can be slower than CPU execution. Allocating an output in the wrong place forces another copy. Hidden synchronization makes latency hard to explain.

**The question.** How should tensor location become part of the execution contract, and when should callers bind memory directly rather than accept default copies?

**Philosophy:** optimize the data path, not the kernel in isolation. Track ownership and location for every value, insert only required transfers, and let callers bind data where the next consumer needs it.

**Think of:** zero-copy networking, NUMA placement, database exchange operators, DMA pipelines.

**ONNX Runtime example:** the execution plan records value locations, transfer nodes bridge providers, and I/O binding accepts device values or target memory descriptions.

**Warning:** “zero copy” still requires lifetime, alignment, allocator, and synchronization compatibility.

[Go deeper](level-2-internals.md#q4-data-placement-and-io-binding) · [Implement it](level-3-code-labs.md#q4-transfer-aware-placement)

## Q5. How can intermediate tensors share memory without overwriting live values?

**Starting point.** A graph can create hundreds of temporary tensors. Most live only between one producer and their last consumer. Reserving a separate peak-sized allocation for each value wastes memory.

**What breaks.** Reusing a buffer too early corrupts a value that another node still needs. Dynamic shapes change required sizes. Concurrent streams can extend a value's physical lifetime beyond its topological last use.

**The question.** How can the runtime map logical tensor values onto fewer physical blocks while proving that incompatible lifetimes never overlap?

**Philosophy:** compute liveness, separate logical identity from physical storage, and reuse only across a proven release boundary. Cache a layout only for a compatible shape and stream signature.

**Think of:** compiler register allocation, stack-frame layout, buffer pools, paged accelerator memory.

**ONNX Runtime example:** the allocation planner assigns reuse and release actions; a run can generate and cache a shape-keyed memory pattern.

**Warning:** a topological lifetime is insufficient when asynchronous device work has not completed.

[Go deeper](level-2-internals.md#q5-lifetime-based-memory-reuse) · [Implement it](level-3-code-labs.md#q5-liveness-buffer-planner)

## Q6. When does an arena allocator help, and when does it hide memory debt?

**Starting point.** Per-tensor device allocations add synchronization and allocator overhead. A session can instead request large regions and split them into reusable chunks.

**What breaks.** A retained arena may make later allocations fast while keeping process or device memory far above live tensor bytes. Size diversity and unlucky request sequences create fragmentation. Unbounded growth can starve neighboring workloads.

**The question.** How should an arena grow, split, merge, cap, and shrink while exposing the difference between useful cache and stranded capacity?

**Philosophy:** amortize expensive allocation behind a bounded pool, but measure live, reserved, fragmented, and releasable bytes separately.

**Think of:** slab allocation, connection pools, page caches, jemalloc arenas.

**ONNX Runtime example:** the best-fit-with-coalescing arena organizes free chunks in bins, extends regions under a strategy and limit, and can release free regions.

**Warning:** shrinking saves capacity but can reintroduce allocation latency and device synchronization.

[Go deeper](level-2-internals.md#q6-arena-allocation) · [Implement it](level-3-code-labs.md#q6-coalescing-arena)

## Q7. How should a runtime use parallelism without multiplying runnable threads?

**Starting point.** Independent graph nodes can run concurrently, and one matrix operation can divide its loop across cores. The application may also run many requests or sessions at once.

**What breaks.** If every request, node, and kernel creates its own full thread team, runnable work exceeds the cores. Context switching and memory-bandwidth contention increase tail latency even though every layer appears “parallel.”

**The question.** Which layer owns concurrency, how large are intra-operation and inter-operation pools, and when should pools be shared across sessions?

**Philosophy:** budget parallelism once across the process. Nested parallel regions must cooperate or collapse, and thread counts must reflect concurrent requests rather than one benchmark run.

**Think of:** work-stealing pools, database worker budgets, structured concurrency, BLAS oversubscription.

**ONNX Runtime example:** session or environment thread pools separate intra-op loop work from inter-op graph work and centralize operator parallel loops.

**Warning:** more threads can reduce throughput when memory bandwidth, not compute, is scarce.

[Go deeper](level-2-internals.md#q7-threading-and-oversubscription) · [Implement it](level-3-code-labs.md#q7-parallelism-budget)

## Q8. How should dependencies remain correct when device work finishes asynchronously?

**Starting point.** A CPU kernel often returns when its output is ready. A GPU launch may return while the device still writes that output. Multiple logical streams can overlap independent work.

**What breaks.** Scheduling a consumer after host launch order does not prove that its input is complete. Synchronizing after every node restores correctness but destroys overlap. Cancellation cannot always stop work already submitted to a device.

**The question.** Where should the plan place waits, notifications, barriers, and cleanup so dependent work observes complete data without serializing independent work?

**Philosophy:** distinguish submission order from completion order. Represent asynchronous dependencies explicitly and release memory only after the completion fence.

**Think of:** futures, event loops, GPU events, distributed happens-before relations.

**ONNX Runtime example:** execution plans contain logical streams, barriers, and notification actions; provider streams and the executor coordinate completion and release.

**Warning:** cancellation is often cooperative. It may stop future dispatch while already submitted device work drains.

[Go deeper](level-2-internals.md#q8-asynchronous-execution) · [Implement it](level-3-code-labs.md#q8-event-fenced-scheduler)

## Q9. When is reduced numerical precision an acceptable execution plan?

**Starting point.** Lower-precision weights and activations reduce model bytes and can use faster hardware kernels. Conversion scales and zero points add their own work, while some operations are much more sensitive to error than others.

**What breaks.** A smaller model can become slower if the provider lacks native kernels or inserts repeated conversions. Average error can hide a failed user cohort. Quantizing every operation with one rule can destroy model quality.

**The question.** Which values may lose precision, which metric defines acceptable loss, and does the target hardware produce an end-to-end win?

**Philosophy:** numerical representation is a measured systems trade, not a file-size switch. Keep a full-precision oracle, calibrate representative data, exclude sensitive operations, and benchmark the target provider.

**Think of:** approximate data structures, lossy compression, mixed precision, storage encodings.

**ONNX Runtime example:** quantization tooling supports calibration, QDQ or quantized-operator graphs, provider-aware kernels, and activation comparison for debugging.

**Warning:** accuracy and speed claims are model-, data-, operator-, and hardware-specific.

[Go deeper](level-2-internals.md#q9-quantization-contract) · [Implement it](level-3-code-labs.md#q9-calibration-and-quality-gate)

## Q10. How should a service keep model preparation off the first live request?

**Starting point.** Creating a session can validate and rewrite the graph, partition it, compile provider subgraphs, prepack weights, load external data, reserve memory, and copy weights to a device. A large model can spend far longer preparing than one inference takes.

**What breaks.** Lazy initialization turns one customer request into a deployment operation. Rebuilding independently on every replica creates slow, inconsistent starts. Publishing an artifact without its provider, runtime, and model metadata can load the wrong compiled state.

**The question.** Which preparation can be performed once, which remains host-specific, and how should a service validate and atomically activate a ready session generation?

**Philosophy:** separate compilation from execution. Build a versioned artifact, validate it against the target runtime and hardware, warm the remaining session state, then switch traffic to one complete generation.

**Think of:** ahead-of-time compilation, prepared queries, immutable index publication, blue-green deployment.

**ONNX Runtime example:** optimized or ORT-format models, execution-provider context, weight prepacking, and bounded external-weight staging move work into session initialization or build time.

**Warning:** a serialized graph does not contain a fleet rollout protocol; the serving layer still owns readiness, atomic publication, draining, and rollback.

[Go deeper](level-2-internals.md#q10-session-preparation-and-publication) · [Implement it](level-3-code-labs.md#q10-prepared-session-generation)
