# SGLang — Level 3: Code Labs
[Radar](../README.md) · [SGLang](README.md) · [Level 1](level-1-philosophy.md) · [Level 2](level-2-internals.md)

## Q1. Radix prefix cache
[Philosophy](level-1-philosophy.md#q1-how-is-the-longest-reusable-prefix-found-across-evolving-requests) · [Interview](level-2-internals.md#q1-radix-prefix-cache)
```python
n = lcp(edge.tokens, tokens); edge = split(edge, n) if n < len(edge.tokens) else edge
```
Implement insert, longest match, reference locks, and leaf eviction; verify paths reconstruct all keys.

## Q2. Request scheduler
[Philosophy](level-1-philosophy.md#q2-how-are-asynchronous-requests-continuously-batched) · [Interview](level-2-internals.md#q2-continuous-scheduling)
```python
batch = continue_decode() or build_prefill(); result = workers.forward(batch); apply(result)
```
Define legal request transitions and fuzz abort, retract, and finish races.

## Q3. Prefill controller
[Philosophy](level-1-philosophy.md#q3-how-do-large-prefills-share-iterations-with-decode) · [Interview](level-2-internals.md#q3-chunked-prefill)
```python
chunk = clamp(chunk + kp * (target_itl - observed_itl), minimum, memory_safe_max)
```
Add smoothing and hysteresis; prove bursty traffic does not cause oscillation.

## Q4. Tiered cache
[Philosophy](level-1-philosophy.md#q4-how-should-kv-state-span-gpu-host-and-storage) · [Interview](level-2-internals.md#q4-hierarchical-cache)
```python
promote(key) if fetch_cost(key) < recompute_cost(key) else recompute(key)
```
Implement `RESIDENT/TRANSFERRING/EVICTING`; never expose incomplete transfer state.

## Q5. KV transfer
[Philosophy](level-1-philosophy.md#q5-when-should-prefill-and-decode-use-separate-fleets) · [Interview](level-2-internals.md#q5-pd-disaggregation)
```python
ticket = decode.reserve(manifest); transport.copy(blocks, ticket.dst); decode.commit(ticket, checksum)
```
Handle copy-before-commit failure, timeout cleanup, duplicate manifests, and generation mismatch.

## Q6. Grammar mask
[Philosophy](level-1-philosophy.md#q6-how-is-schema-conforming-output-guaranteed) · [Interview](level-2-internals.md#q6-constrained-decoding)
```python
logits[~automaton.allowed_tokens(state)] = -inf; state = automaton.advance(sample(logits))
```
Implement JSON escape states and deterministic jump-forward; test multi-byte tokenizer boundaries.

## Q7. Speculation controller
[Philosophy](level-1-philosophy.md#q7-how-should-speculation-depth-adapt) · [Interview](level-2-internals.md#q7-adaptive-speculation)
```python
k = clamp(k + (1 if ema(saved_target_ms - draft_ms - verify_ms) > margin else -1), 1, max_k)
```
Add memory/ITL constraints and hysteresis; test abrupt acceptance shifts.

## Q8. Locality router
[Philosophy](level-1-philosophy.md#q8-how-should-replicas-be-selected-when-both-load-and-cache-locality-matter) · [Interview](level-2-internals.md#q8-routing-and-parallelism)
```python
score = queue_ms(replica) + prefix_miss_ms(replica, request) + transfer_ms(replica)
```
Add stale-telemetry bounds, random tie-breaking, and hysteresis; demonstrate no herd oscillation.

## Q9. Token-slot pool
[Philosophy](level-1-philosophy.md#q9-how-do-tokens-map-safely-to-physical-kv-slots) · [Interview](level-2-internals.md#q9-memory-pool-indirection)
```python
for pos, slot in zip(positions, reserved): assert owner[slot] is None; owner[slot] = request_id
```
Implement rollback, sharing, and double-free detection; property-test ownership uniqueness.

## Q10. Fenced pipeline
[Philosophy](level-1-philosophy.md#q10-how-does-a-multi-process-serving-pipeline-preserve-ownership) · [Interview](level-2-internals.md#q10-serving-pipeline)
```python
if msg.generation == live_generation.get(msg.request_id): bounded_next_stage.put(msg)
```
Propagate cancellation and restart a worker without accepting stale messages; monitor queue age.
