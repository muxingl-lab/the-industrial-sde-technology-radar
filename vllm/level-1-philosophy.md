# vLLM — Level 1: Philosophy

[Radar](../README.md) · [vLLM](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

## Q1. How can per-request memory grow without reserving its maximum size?
**Starting point.** As a model generates text, it keeps intermediate state for every token it has processed. Each new token reads that state. The server does not know how long a request will run: one may stop after 20 tokens, while another may continue for thousands.

**What breaks.** Reserving the maximum possible space for every request wastes most of the accelerator's memory. Allocating only the exact space needed now creates a different problem: the server may have to move the state whenever the request grows.

**The question.** How can request state grow on demand, keep stable references, and remain efficient to read in a batch when its physical memory is not contiguous?

**Philosophy:** separate logical addresses from fixed-size physical blocks. vLLM applies virtual-memory-style paging to KV cache. **Warning:** paging trades external fragmentation for block tables, last-block waste, and allocator coordination. [Deep dive](level-2-internals.md#q1-paged-kv-cache) · [Lab](level-3-code-labs.md#q1-paged-kv-allocator)

## Q2. How do asynchronous requests share the GPU efficiently?
**Starting point.** A GPU is most efficient when it runs many requests together. Serving traffic, however, arrives continuously, and requests finish at different times.

**What breaks.** In a fixed batch, short requests leave empty slots after they finish. New requests still wait until the longest request completes, even though the GPU has spare capacity.

**The question.** How can the runtime rebuild the batch after every model step without losing any request's progress or memory state?

**Philosophy:** schedule every iteration and budget tokens, not whole requests. Continuous batching admits and removes work as sequences evolve. **Warning:** packing for throughput can starve long prompts or hurt inter-token latency. [Deep dive](level-2-internals.md#q2-continuous-batching) · [Lab](level-3-code-labs.md#q2-token-budget-scheduler)

## Q3. How can long inputs coexist with requests that need one quick step?
**Starting point.** A new request may contain thousands of input tokens that the model must process before producing its first output. At the same time, existing requests need one small step each to keep their output streams moving.

**What breaks.** Processing the long input in one shot pauses every active stream. Always serving the small steps has the opposite failure: long requests may never start. Very small chunks improve fairness but make GPU execution less efficient.

**The question.** How should the scheduler divide and mix these two kinds of work to balance first-token latency, inter-token latency, and throughput?

**Philosophy:** split monopolizing work into resumable chunks and co-schedule phases with different SLOs. **Warning:** tiny chunks add overhead and reduce kernel efficiency. [Deep dive](level-2-internals.md#q3-chunked-prefill) · [Lab](level-3-code-labs.md#q3-chunked-prefill)

## Q4. When is prefix computation safely reusable?
**Starting point.** Many requests repeat the same system prompt, document, or conversation history. Given the same inputs, the model computes the same intermediate state for that shared prefix.

**What breaks.** Recomputing the prefix wastes GPU time. Reusing it with an incomplete cache key is worse: a different model, adapter, image, or tenant context can make apparently similar prefixes produce different state. Shared memory also cannot be freed while another request still uses it.

**The question.** What must define the identity and lifetime of a reusable prefix so that sharing is both useful and correct?

**Philosophy:** use immutable, content-addressed blocks whose identity includes every semantic input. **Warning:** omitted adapter, modality, salt, or model context creates silent wrong reuse. [Deep dive](level-2-internals.md#q4-prefix-caching) · [Lab](level-3-code-labs.md#q4-prefix-cache)

## Q5. What happens when active requests need more accelerator memory than exists?
**Starting point.** Every active request consumes accelerator memory, and that memory grows as the request produces more tokens. Each request may be valid on its own while the active set is too large in aggregate.

**What breaks.** Optimistic allocation can crash the worker with an out-of-memory error. Reserving every request's maximum possible size prevents the crash but leaves much of the device unused.

**The question.** How should the engine admit, pause, reject, or preempt work when it cannot know each request's final memory demand?

**Philosophy:** overload requires explicit admission, reservation, preemption, or rejection. **Warning:** repeated preemption wastes compute and can thrash. [Deep dive](level-2-internals.md#q5-admission-and-preemption) · [Lab](level-3-code-labs.md#q5-admission-control)

## Q6. How can cheap predictions reduce calls to an expensive model?
**Starting point.** Normal generation runs the full model once for every output token. Some stretches of text are predictable enough that a cheaper model or a pattern matcher can propose several likely tokens at once.

**What breaks.** A cheap proposal is not authoritative. Committing a wrong proposal changes the model's output, while verifying poor proposals can cost more than ordinary generation.

**The question.** How can the server verify several proposed tokens in one target-model step, preserve the target distribution, and use speculation only when it saves work?

**Philosophy:** let cheap work speculate and authoritative work verify; never commit unverified state. **Warning:** low acceptance adds cost without saving target steps. [Deep dive](level-2-internals.md#q6-speculative-decoding) · [Lab](level-3-code-labs.md#q6-speculate-and-verify)

## Q7. Which parallelism dimension should scale the model?
**Starting point.** A model may be too large for one accelerator. Even when it fits, one copy may not serve enough requests.

**What breaks.** Several scaling methods are available, but they solve different problems. Splitting individual operations, splitting layers, replicating the model, splitting long inputs, and distributing experts all create different communication and synchronization costs.

**The question.** Which dimension should be partitioned for this model, hardware topology, and workload—and is the goal to fit one request or serve more requests?

**Philosophy:** partition the scarce dimension, then price communication, synchronization, imbalance, and failure domains. **Warning:** more devices can be slower when collectives dominate. [Deep dive](level-2-internals.md#q7-parallelism) · [Lab](level-3-code-labs.md#q7-parallelism-planner)

## Q8. When should repeated GPU work be recorded and replayed?
**Starting point.** Serving repeatedly launches nearly the same sequence of GPU kernels. The model work runs on the accelerator, but Python dispatch, framework bookkeeping, and kernel launches still consume time on every iteration.

**What breaks.** Recording the execution once can remove that overhead, but only for compatible input shapes and memory addresses. Real requests create many batch sizes, token counts, and optional paths. Capturing all of them consumes too much memory.

**The question.** Which execution shapes are worth recording, how much padding is acceptable, and when should the runtime use ordinary dynamic execution?

**Philosophy:** capture stable shapes and replay them, retaining eager fallback outside the capture contract. **Warning:** graph memory and shape proliferation can erase gains. [Deep dive](level-2-internals.md#q8-execution-shapes) · [Lab](level-3-code-labs.md#q8-shape-cache)

## Q9. Who owns request lifecycle versus device execution?
**Starting point.** Request validation, scheduling, device execution, and output streaming may run in different processes. Their messages can be delayed, duplicated, or delivered after a component restarts.

**What breaks.** A request can be cancelled while device work is still running. A late result can arrive after the request ID has been reused. If several components own lifecycle state, the system may publish stale output, leak memory, or free the same memory twice.

**The question.** Which component owns request state, and how should every other component prove that its message still belongs to the current request generation?

**Philosophy:** one engine core owns scheduling state; workers execute explicit plans and return results. **Warning:** stale results require generation fencing and idempotent cancellation. [Deep dive](level-2-internals.md#q9-engine-ownership) · [Lab](level-3-code-labs.md#q9-fenced-worker)

## Q10. How do streaming and cancellation stay bounded?
**Starting point.** The model can produce tokens faster than an HTTP client or proxy can consume them. Between model execution and the network sit several queues and processing stages.

**What breaks.** An unbounded queue turns one slow client into growing server memory. Closing the socket is not enough: the request may still occupy scheduler slots and accelerator memory. Cancellation can also race with normal completion.

**The question.** Where should the system apply backpressure, and how should cancellation release every resource exactly once across all stages?

**Philosophy:** bound every queue and propagate cancellation through output, scheduler, and KV ownership. **Warning:** an HTTP disconnect alone may leak live engine work. [Deep dive](level-2-internals.md#q10-streaming-and-cancellation) · [Lab](level-3-code-labs.md#q10-bounded-stream)
