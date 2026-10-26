# vLLM — Level 3: Code Labs
[Radar](../README.md) · [vLLM](README.md) · [Level 1](level-1-philosophy.md) · [Level 2](level-2-internals.md)

## Q1. Paged KV allocator
[Philosophy](level-1-philosophy.md#q1-how-do-variable-length-sequences-avoid-worst-case-contiguous-allocation) · [Interview](level-2-internals.md#q1-paged-kv-cache)
```python
def release(blocks):
    for b in blocks:
        refs[b] -= 1
        if refs[b] == 0: free.append(b)
```
Implement allocation, sharing, and atomic rollback. Property-test capacity conservation and unique ownership.

## Q2. Token-budget scheduler
[Philosophy](level-1-philosophy.md#q2-how-do-asynchronous-requests-share-the-gpu-efficiently) · [Interview](level-2-internals.md#q2-continuous-batching)
```python
for r in running + waiting:
    n = min(r.ready_tokens(), budget)
    if n and kv.reserve(r, n): plan.append((r, n)); budget -= n
```
Add priority aging and rollback; replay mixed prompt lengths and measure TTFT, ITL, throughput, and starvation.

## Q3. Chunked prefill
[Philosophy](level-1-philosophy.md#q3-how-do-long-prefills-coexist-with-latency-sensitive-decode) · [Interview](level-2-internals.md#q3-chunked-prefill)
```python
chunk = min(req.prompt_remaining, max_chunk, budget_after_decode)
```
Add prefill aging and plot P99 ITL versus chunk size.

## Q4. Prefix cache
[Philosophy](level-1-philosophy.md#q4-when-is-prefix-computation-safely-reusable) · [Interview](level-2-internals.md#q4-prefix-caching)
```python
key = sha256(encode(parent_hash, tokens, model, adapter, modality, tenant_salt)).digest()
```
Implement longest full-block match, refcounts, and eviction of only unreferenced blocks; test isolation.

## Q5. Admission control
[Philosophy](level-1-philosophy.md#q5-what-happens-when-requested-work-exceeds-kv-capacity) · [Interview](level-2-internals.md#q5-admission-and-preemption)
```python
decision = RUN if pool.can_reserve(req.blocks) else PREEMPT if victim(req) else WAIT
```
Add queue caps and preemption cooldown; inject exceptions and prove no reservation leaks.

## Q6. Speculate and verify
[Philosophy](level-1-philosophy.md#q6-how-can-several-tokens-be-produced-per-authoritative-model-step) · [Interview](level-2-internals.md#q6-speculative-decoding)
```python
draft = proposer(prefix, k); scores = target.score(prefix, draft); commit(verify(draft, scores))
```
Implement greedy acceptance, then rejection sampling; measure accepted tokens per target step.

## Q7. Parallelism planner
[Philosophy](level-1-philosophy.md#q7-which-parallelism-dimension-should-scale-the-model) · [Interview](level-2-internals.md#q7-parallelism)
```python
cost = memory_overflow(plan) * INF + collective_ms(plan, topology) + imbalance(plan)
```
Enumerate TP/PP/DP/EP plans and reject topology-crossing collectives that violate the SLO.

## Q8. Shape cache
[Philosophy](level-1-philosophy.md#q8-how-is-repeated-gpu-launch-overhead-removed) · [Interview](level-2-internals.md#q8-execution-shapes)
```python
return graphs[shape].replay(pad(batch, shape)) if padding_ratio < .2 else eager(batch)
```
Select capture shapes from a workload histogram under a graph-memory budget.

## Q9. Fenced worker
[Philosophy](level-1-philosophy.md#q9-who-owns-request-lifecycle-versus-device-execution) · [Interview](level-2-internals.md#q9-engine-ownership)
```python
if req and result.generation == req.generation: req.accept(result)
```
Model cancel-versus-completion races and prove resources are released exactly once.

## Q10. Bounded stream
[Philosophy](level-1-philosophy.md#q10-how-do-streaming-and-cancellation-stay-bounded) · [Interview](level-2-internals.md#q10-streaming-and-cancellation)
```python
try: output.put_nowait(chunk)
except QueueFull: await engine.abort(request_id, generation)
```
Add coalescing, timeout, and idempotent abort; fault-test disconnect at every state.

