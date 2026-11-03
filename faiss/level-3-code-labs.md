# FAISS Source Study — Level 3: Code Labs

[Radar home](../README.md) · [FAISS home](README.md) · [Level 1](level-1-philosophy.md) · [Level 2](level-2-internals.md)

These Python fragments expose the mechanism; production FAISS uses optimized C++ and accelerator kernels.

## Q1. Exact top-k and recall

[Philosophy](level-1-philosophy.md#q1-why-must-an-approximate-retrieval-system-keep-an-exact-baseline) · [Interview answer](level-2-internals.md#q1-exact-baseline)

```python
def exact_topk(query, vectors, k):
    scored = [(sum((a - b) ** 2 for a, b in zip(query, v)), i)
              for i, v in enumerate(vectors)]
    return [i for _, i in sorted(scored)[:k]]

def recall_at_k(expected, actual):
    assert len(expected) == len(actual)
    return len(set(expected) & set(actual)) / len(expected)
```

**Handwrite:** add cosine similarity with explicit normalization. **Test:** identical vectors, ties, fewer than k candidates, and a deliberately missed nearest neighbor.

## Q2. Budgeted configuration selection

[Philosophy](level-1-philosophy.md#q2-how-should-a-service-budget-recall-latency-and-bytes-per-vector) · [Interview answer](level-2-internals.md#q2-quality-and-resource-budget)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Result:
    name: str; recall: float; p99_ms: float; bytes_per_vector: float

def choose(results, min_recall, max_p99, max_bytes):
    feasible = [r for r in results if r.recall >= min_recall
                and r.p99_ms <= max_p99 and r.bytes_per_vector <= max_bytes]
    if not feasible:
        raise ValueError("no configuration satisfies the contract")
    return min(feasible, key=lambda r: (r.p99_ms, r.bytes_per_vector))
```

**Handwrite:** return the Pareto frontier instead of one winner. **Test:** a fast configuration below the recall floor must never win.

## Q3. Miniature IVF

[Philosophy](level-1-philosophy.md#q3-how-can-an-inverted-index-search-less-data-while-retaining-a-quality-control) · [Interview answer](level-2-internals.md#q3-inverted-file-search)

```python
class MiniIVF:
    def __init__(self, centroids):
        self.centroids, self.lists = centroids, [[] for _ in centroids]

    def add(self, item_id, vector):
        c = exact_topk(vector, self.centroids, 1)[0]
        self.lists[c].append((item_id, vector))

    def search(self, query, k, nprobe):
        probes = exact_topk(query, self.centroids, nprobe)
        candidates = [item for p in probes for item in self.lists[p]]
        scored = [(sum((a-b)**2 for a,b in zip(query, v)), i) for i,v in candidates]
        return [i for _, i in sorted(scored)[:k]]
```

**Handwrite:** cap scanned vectors as well as probed lists. **Test:** construct a boundary query whose true neighbor is missed at `nprobe=1` and found at `nprobe=2`.

## Q4. Bounded best-first search

[Philosophy](level-1-philosophy.md#q4-when-should-graph-traversal-replace-scanning-candidate-lists) · [Interview answer](level-2-internals.md#q4-graph-search)

```python
import heapq

def graph_search(start, neighbors, distance, budget):
    frontier, seen, best = [(distance(start), start)], {start}, []
    while frontier and len(seen) <= budget:
        d, node = heapq.heappop(frontier)
        best.append((d, node))
        for nxt in neighbors[node]:
            if nxt not in seen:
                seen.add(nxt)
                heapq.heappush(frontier, (distance(nxt), nxt))
    return best
```

**Handwrite:** keep only `ef` best results and stop when the closest candidate cannot improve them. **Test:** cycles, disconnected components, and a strict visit budget.

## Q5. Product quantization core

[Philosophy](level-1-philosophy.md#q5-when-should-vectors-be-compressed-and-how-should-quantization-loss-be-measured) · [Interview answer](level-2-internals.md#q5-product-quantization)

```python
def encode(vector, codebooks):
    width = len(vector) // len(codebooks)
    return [exact_topk(vector[m*width:(m+1)*width], book, 1)[0]
            for m, book in enumerate(codebooks)]

def adc_distance(query, code, codebooks):
    width, total = len(query) // len(codebooks), 0.0
    for m, word in enumerate(code):
        sub = query[m*width:(m+1)*width]
        total += sum((a-b)**2 for a,b in zip(sub, codebooks[m][word]))
    return total
```

**Handwrite:** precompute query-to-codeword tables. **Test:** encoding followed by ADC must match distance to the explicitly reconstructed vector.

## Q6. Drift trigger

[Philosophy](level-1-philosophy.md#q6-how-should-training-data-and-distribution-drift-affect-an-index) · [Interview answer](level-2-internals.md#q6-training-and-drift)

```python
def should_rebuild(metrics, policy, last_build_age_days):
    if last_build_age_days < policy["min_age_days"]:
        return False
    return (metrics["recall"] < policy["min_recall"] or
            metrics["max_list_over_mean"] > policy["max_imbalance"] or
            metrics["quantization_error"] > policy["max_q_error"])
```

**Handwrite:** add two consecutive bad windows before triggering. **Test:** one transient breach must not start a rebuild.

## Q7. Placement cost model

[Philosophy](level-1-philosophy.md#q7-when-should-search-state-live-on-cpu-versus-gpu) · [Interview answer](level-2-internals.md#q7-cpugpu-placement)

```python
def choose_device(batch, cpu_ms, gpu_kernel_ms, transfer_ms, queue_ms, p99_budget):
    gpu_total = transfer_ms(batch) + queue_ms(batch) + gpu_kernel_ms(batch)
    cpu_total = cpu_ms(batch)
    feasible = [(cpu_total, "cpu"), (gpu_total, "gpu")]
    feasible = [x for x in feasible if x[0] <= p99_budget]
    return min(feasible)[1] if feasible else "reject"
```

**Handwrite:** include device-memory admission. **Test:** GPU wins large batches but loses when transfer dominates a single query.

## Q8. Generation manager

[Philosophy](level-1-philosophy.md#q8-how-should-a-serving-system-replace-a-rebuilt-index-without-exposing-a-partial-generation) · [Interview answer](level-2-internals.md#q8-generation-publication)

```python
from threading import Lock

class GenerationManager:
    def __init__(self, initial):
        self._active, self._lock = initial, Lock()

    def acquire(self):
        with self._lock:
            self._active.readers += 1
            return self._active

    def publish(self, candidate):
        candidate.validate()
        with self._lock:
            old, self._active = self._active, candidate
        old.retire_when_unused()
```

**Handwrite:** make `release()` race-safe and reject a generation with the wrong embedding contract. **Test:** concurrent readers must observe either the old or new generation, never a mixture.
