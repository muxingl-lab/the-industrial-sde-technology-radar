# vLLM — Level 1: Philosophy

[Radar](../README.md) · [vLLM](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

## Q1. How do variable-length sequences avoid worst-case contiguous allocation?
**Philosophy:** separate logical addresses from fixed-size physical blocks. vLLM applies virtual-memory-style paging to KV cache. **Warning:** paging trades external fragmentation for block tables, last-block waste, and allocator coordination. [Deep dive](level-2-internals.md#q1-paged-kv-cache) · [Lab](level-3-code-labs.md#q1-paged-kv-allocator)

## Q2. How do asynchronous requests share the GPU efficiently?
**Philosophy:** schedule every iteration and budget tokens, not whole requests. Continuous batching admits and removes work as sequences evolve. **Warning:** packing for throughput can starve long prompts or hurt inter-token latency. [Deep dive](level-2-internals.md#q2-continuous-batching) · [Lab](level-3-code-labs.md#q2-token-budget-scheduler)

## Q3. How do long prefills coexist with latency-sensitive decode?
**Philosophy:** split monopolizing work into resumable chunks and co-schedule phases with different SLOs. **Warning:** tiny chunks add overhead and reduce kernel efficiency. [Deep dive](level-2-internals.md#q3-chunked-prefill) · [Lab](level-3-code-labs.md#q3-chunked-prefill)

## Q4. When is prefix computation safely reusable?
**Philosophy:** use immutable, content-addressed blocks whose identity includes every semantic input. **Warning:** omitted adapter, modality, salt, or model context creates silent wrong reuse. [Deep dive](level-2-internals.md#q4-prefix-caching) · [Lab](level-3-code-labs.md#q4-prefix-cache)

## Q5. What happens when requested work exceeds KV capacity?
**Philosophy:** overload requires explicit admission, reservation, preemption, or rejection. **Warning:** repeated preemption wastes compute and can thrash. [Deep dive](level-2-internals.md#q5-admission-and-preemption) · [Lab](level-3-code-labs.md#q5-admission-control)

## Q6. How can several tokens be produced per authoritative model step?
**Philosophy:** let cheap work speculate and authoritative work verify; never commit unverified state. **Warning:** low acceptance adds cost without saving target steps. [Deep dive](level-2-internals.md#q6-speculative-decoding) · [Lab](level-3-code-labs.md#q6-speculate-and-verify)

## Q7. Which parallelism dimension should scale the model?
**Philosophy:** partition the scarce dimension, then price communication, synchronization, imbalance, and failure domains. **Warning:** more devices can be slower when collectives dominate. [Deep dive](level-2-internals.md#q7-parallelism) · [Lab](level-3-code-labs.md#q7-parallelism-planner)

## Q8. How is repeated GPU launch overhead removed?
**Philosophy:** capture stable shapes and replay them, retaining eager fallback outside the capture contract. **Warning:** graph memory and shape proliferation can erase gains. [Deep dive](level-2-internals.md#q8-execution-shapes) · [Lab](level-3-code-labs.md#q8-shape-cache)

## Q9. Who owns request lifecycle versus device execution?
**Philosophy:** one engine core owns scheduling state; workers execute explicit plans and return results. **Warning:** stale results require generation fencing and idempotent cancellation. [Deep dive](level-2-internals.md#q9-engine-ownership) · [Lab](level-3-code-labs.md#q9-fenced-worker)

## Q10. How do streaming and cancellation stay bounded?
**Philosophy:** bound every queue and propagate cancellation through output, scheduler, and KV ownership. **Warning:** an HTTP disconnect alone may leak live engine work. [Deep dive](level-2-internals.md#q10-streaming-and-cancellation) · [Lab](level-3-code-labs.md#q10-bounded-stream)

