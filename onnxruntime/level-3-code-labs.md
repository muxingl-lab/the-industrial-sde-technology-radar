# ONNX Runtime Source Study — Level 3: Code Labs

[Radar home](../README.md) · [ONNX Runtime home](README.md) · [Level 1](level-1-philosophy.md) · [Level 2](level-2-internals.md)

These Python mechanisms make the invariants visible. Production ONNX Runtime implements them in C++ with provider-specific allocators, kernels, streams, and ABI boundaries.

## Q1. Graph contract validator

[Philosophy](level-1-philosophy.md#q1-how-can-a-runtime-reject-an-incompatible-computation-graph-before-it-reaches-hardware) · [Interview answer](level-2-internals.md#q1-model-contract-validation)

```python
def validate_graph(nodes, inputs, schemas, opset):
    available = dict(inputs)
    for node in topological_sort(nodes):
        schema = schemas.get((node.op, opset))
        if schema is None:
            raise ValueError(f"unsupported operator: {node.op}@{opset}")
        args = [available[name] for name in node.inputs]
        schema.check_attributes(node.attrs)
        output_types = schema.infer(args, node.attrs)  # may retain unknown dims
        for name, value_type in zip(node.outputs, output_types):
            if name in available:
                raise ValueError(f"duplicate value: {name}")
            available[name] = value_type
    return available
```

**Handwrite:** report all independent validation errors without continuing after an unsafe dependency. **Test:** missing input, duplicate output, unsupported opset, contradictory dimensions, and a valid symbolic batch dimension.

## Q2. Safe rewrite pass

[Philosophy](level-1-philosophy.md#q2-how-can-a-runtime-rewrite-a-computation-graph-without-changing-its-result) · [Interview answer](level-2-internals.md#q2-graph-transformation)

```python
def fuse_matmul_add(graph):
    changed = False
    for add in list(graph.nodes):
        matmul = graph.single_producer(add.inputs[0])
        if not matmul or matmul.op != "MatMul":
            continue
        if graph.consumer_count(matmul.outputs[0]) != 1:
            continue
        if not broadcast_compatible(add.inputs[1], matmul.outputs[0]):
            continue
        graph.replace([matmul, add], Node("Gemm", matmul.inputs + [add.inputs[1]], add.outputs))
        changed = True
    if changed:
        graph.resolve()
    return changed
```

**Handwrite:** preserve names needed as public graph outputs. **Test:** compare original and rewritten graphs across broadcast shapes and floating-point tolerances.

## Q3. Capability-aware partitioner

[Philosophy](level-1-philosophy.md#q3-how-should-one-graph-be-divided-across-backends-with-different-capabilities) · [Interview answer](level-2-internals.md#q3-execution-provider-partitioning)

```python
def partition(graph, providers):
    owner = {}
    for provider in providers:  # caller-defined priority
        for group in provider.capabilities(graph, owner):
            if all(node not in owner for node in group.nodes):
                compiled = provider.compile(group)
                for node in group.nodes:
                    owner[node] = (provider.name, compiled)
    missing = [node for node in graph.nodes if node not in owner]
    if missing:
        raise ValueError(f"no execution provider for {missing}")
    return owner
```

**Handwrite:** score claims using transfer bytes and workspace instead of accepting every claim. **Test:** overlapping claims, unsupported types, CPU fallback, and a provider compile failure.

## Q4. Transfer-aware placement

[Philosophy](level-1-philosophy.md#q4-how-do-you-stop-device-transfers-from-erasing-accelerator-gains) · [Interview answer](level-2-internals.md#q4-data-placement-and-io-binding)

```python
def insert_transfers(graph, owner, value_device):
    for node in graph.topological_nodes():
        target = owner[node].device
        for i, value in enumerate(node.inputs):
            source = value_device[value]
            if source != target:
                copied = graph.add_copy(value, source, target)
                node.inputs[i] = copied
                value_device[copied] = target
        for output in node.outputs:
            value_device[output] = target
```

**Handwrite:** coalesce one transfer shared by several consumers on the same target. **Test:** count bytes for alternating CPU/GPU nodes and reject a placement slower than all-CPU execution.

## Q5. Liveness buffer planner

[Philosophy](level-1-philosophy.md#q5-how-can-intermediate-tensors-share-memory-without-overwriting-live-values) · [Interview answer](level-2-internals.md#q5-lifetime-based-memory-reuse)

```python
def plan_buffers(values):
    active, free, plan = [], [], {}
    for value in sorted(values, key=lambda v: v.first_use):
        expired = [a for a in active if a.last_use < value.first_use]
        for old in expired:
            active.remove(old); free.append(plan[old.name])
        block = next((b for b in free if b.device == value.device and b.size >= value.size), None)
        if block:
            free.remove(block)
        else:
            block = Block(value.device, value.size)
        plan[value.name] = block
        active.append(value)
    return plan
```

**Handwrite:** extend `last_use` to a stream-completion event. **Test:** randomized executions must never place simultaneously live values in overlapping storage.

## Q6. Coalescing arena

[Philosophy](level-1-philosophy.md#q6-when-does-an-arena-allocator-help-and-when-does-it-hide-memory-debt) · [Interview answer](level-2-internals.md#q6-arena-allocation)

```python
class Arena:
    def __init__(self, limit):
        self.limit, self.reserved, self.chunks = limit, 0, []

    def allocate(self, size):
        chunk = min((c for c in self.chunks if c.free and c.size >= size),
                    key=lambda c: c.size, default=None)
        if chunk is None:
            grow = round_region(size)
            if self.reserved + grow > self.limit:
                raise MemoryError
            chunk = self.extend(grow); self.reserved += grow
        result = chunk.split(size) if chunk.can_split(size) else chunk
        result.free = False
        return result

    def free(self, chunk):
        chunk.free = True
        self.coalesce_with_free_neighbors(chunk)
```

**Handwrite:** return wholly free regions during `shrink`. **Test:** after random allocation/free sequences, chunks cover each region exactly once and never overlap.

## Q7. Parallelism budget

[Philosophy](level-1-philosophy.md#q7-how-should-a-runtime-use-parallelism-without-multiplying-runnable-threads) · [Interview answer](level-2-internals.md#q7-threading-and-oversubscription)

```python
def thread_budget(cores, concurrent_runs, graph_parallel=False):
    if concurrent_runs <= 0:
        raise ValueError("concurrent_runs must be positive")
    per_run = max(1, cores // concurrent_runs)
    return {
        "intra_op": per_run,
        "inter_op": min(per_run, 2) if graph_parallel else 1,
        "nested_kernel_threads": 1,
    }
```

**Handwrite:** allocate a shared token budget dynamically across active runs. **Test:** total runnable workers never exceeds the process budget as concurrency rises.

## Q8. Event-fenced scheduler

[Philosophy](level-1-philosophy.md#q8-how-should-dependencies-remain-correct-when-device-work-finishes-asynchronously) · [Interview answer](level-2-internals.md#q8-asynchronous-execution)

```python
def execute(plan, streams, cancelled):
    events = {}
    for step in plan:
        if cancelled():
            break
        stream = streams[step.stream]
        for dependency in step.wait_for:
            stream.wait(events[dependency])
        step.kernel.launch(stream)
        events[step.id] = stream.record_event()
    for event in events.values():
        event.wait()  # safe cleanup even after cooperative cancellation
```

**Handwrite:** release a buffer after every event that uses it completes. **Test:** delay producers on separate streams and assert that no consumer reads an incomplete value.

## Q9. Calibration and quality gate

[Philosophy](level-1-philosophy.md#q9-when-is-reduced-numerical-precision-an-acceptable-execution-plan) · [Interview answer](level-2-internals.md#q9-quantization-contract)

```python
def symmetric_int8_params(samples):
    bound = max(abs(x) for sample in samples for x in sample)
    return max(bound / 127.0, 1e-12)

def quantize(values, scale):
    return [max(-127, min(127, round(x / scale))) for x in values]

def accept(candidate_metrics, baseline_metrics, limits):
    return (baseline_metrics["quality"] - candidate_metrics["quality"] <= limits["quality_drop"]
            and candidate_metrics["p99_ms"] <= limits["p99_ms"]
            and candidate_metrics["bytes"] <= limits["bytes"])
```

**Handwrite:** percentile or histogram-based calibration that resists outliers. **Test:** a smaller artifact that misses the quality floor or runs slower must fail the gate.

## Q10. Prepared session generation

[Philosophy](level-1-philosophy.md#q10-how-should-a-service-keep-model-preparation-off-the-first-live-request) · [Interview answer](level-2-internals.md#q10-session-preparation-and-publication)

```python
class SessionGeneration:
    def __init__(self, manifest, build_session):
        self.manifest, self.build_session = manifest, build_session
        self.session, self.readers = None, 0

    def prepare(self, host):
        self.manifest.verify(host)
        self.session = self.build_session(self.manifest.artifact)
        for inputs in self.manifest.warmup_inputs:
            self.session.run(inputs)
        self.manifest.run_smoke_tests(self.session)

def publish(manager, candidate):
    if candidate.session is None:
        raise ValueError("generation is not ready")
    old = manager.atomic_swap(candidate)
    old.retire_after_readers_drain()
```

**Handwrite:** enforce peak-memory admission for old plus new sessions. **Test:** concurrent requests observe one complete generation, and a failed warmup leaves the old generation active.
