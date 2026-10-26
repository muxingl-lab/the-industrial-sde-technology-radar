# vLLM — Level 1: Philosophy

[Radar](../README.md) · [vLLM](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

## Q1. How do variable-length sequences avoid worst-case contiguous allocation?
**Problem story:** A restaurant accepts parties that may stay for five minutes or five hours, but nobody knows in advance. Reserving an entire room for every party wastes most of the building; putting each growing party at one fixed table eventually forces expensive moves. We need to give each party more space as needed, without requiring its seats to remain physically adjacent.

**Philosophy:** separate logical addresses from fixed-size physical blocks. vLLM applies virtual-memory-style paging to KV cache. **Warning:** paging trades external fragmentation for block tables, last-block waste, and allocator coordination. [Deep dive](level-2-internals.md#q1-paged-kv-cache) · [Lab](level-3-code-labs.md#q1-paged-kv-allocator)

## Q2. How do asynchronous requests share the GPU efficiently?
**Problem story:** Jobs arrive continuously. Some need one more small step; others have hundreds of steps left. If we form a group once and keep it together until everyone finishes, fast jobs wait for the slowest member and newly arrived work waits for the whole group. We need to rebuild the group repeatedly without wasting the machine.

**Philosophy:** schedule every iteration and budget tokens, not whole requests. Continuous batching admits and removes work as sequences evolve. **Warning:** packing for throughput can starve long prompts or hurt inter-token latency. [Deep dive](level-2-internals.md#q2-continuous-batching) · [Lab](level-3-code-labs.md#q2-token-budget-scheduler)

## Q3. How do long prefills coexist with latency-sensitive decode?
**Problem story:** A checkout lane serves customers buying one item and customers unloading several carts. Serving a giant cart without interruption maximizes that customer's progress but freezes everyone else. Switching after every item is fair but wastes time. We need a useful chunk size and a rule for mixing long setup work with tiny urgent steps.

**Philosophy:** split monopolizing work into resumable chunks and co-schedule phases with different SLOs. **Warning:** tiny chunks add overhead and reduce kernel efficiency. [Deep dive](level-2-internals.md#q3-chunked-prefill) · [Lab](level-3-code-labs.md#q3-chunked-prefill)

## Q4. When is prefix computation safely reusable?
**Problem story:** Thousands of reports begin with the same 100-page handbook and add a short personalized appendix. Re-reading the handbook for every report is wasteful. But two handbooks that look similar may differ by one policy, customer, image, or model version; reusing the wrong result would silently corrupt the answer.

**Philosophy:** use immutable, content-addressed blocks whose identity includes every semantic input. **Warning:** omitted adapter, modality, salt, or model context creates silent wrong reuse. [Deep dive](level-2-internals.md#q4-prefix-caching) · [Lab](level-3-code-labs.md#q4-prefix-cache)

## Q5. What happens when requested work exceeds KV capacity?
**Problem story:** A workshop has a fixed number of benches. Started projects occupy benches until completion, new projects keep arriving, and some projects unexpectedly expand. Pretending space is unlimited ends in a crash. The workshop must decide what may start, what must wait, and whether interrupting old work is ever worth the waste.

**Philosophy:** overload requires explicit admission, reservation, preemption, or rejection. **Warning:** repeated preemption wastes compute and can thrash. [Deep dive](level-2-internals.md#q5-admission-and-preemption) · [Lab](level-3-code-labs.md#q5-admission-control)

## Q6. How can several tokens be produced per authoritative model step?
**Problem story:** A senior reviewer is slow and expensive, while a junior can draft several likely next lines quickly. Reviewing a batch can be cheaper than asking the senior to write every line, but only if rejected drafts never leak into the final document and the junior is accurate often enough.

**Philosophy:** let cheap work speculate and authoritative work verify; never commit unverified state. **Warning:** low acceptance adds cost without saving target steps. [Deep dive](level-2-internals.md#q6-speculative-decoding) · [Lab](level-3-code-labs.md#q6-speculate-and-verify)

## Q7. Which parallelism dimension should scale the model?
**Problem story:** A job no longer fits on one machine. We can split every calculation across machines, assign different stages to different machines, or make several complete teams handle different customers. Each choice moves different amounts of data and waits at different barriers; adding machines is not automatically faster.

**Philosophy:** partition the scarce dimension, then price communication, synchronization, imbalance, and failure domains. **Warning:** more devices can be slower when collectives dominate. [Deep dive](level-2-internals.md#q7-parallelism) · [Lab](level-3-code-labs.md#q7-parallelism-planner)

## Q8. How is repeated GPU launch overhead removed?
**Problem story:** A factory repeats nearly the same assembly process thousands of times, yet supervisors reconstruct and approve the plan before every run. Recording and replaying a proven plan saves overhead—until an unusual order has a different shape and no longer fits the recording.

**Philosophy:** capture stable shapes and replay them, retaining eager fallback outside the capture contract. **Warning:** graph memory and shape proliferation can erase gains. [Deep dive](level-2-internals.md#q8-execution-shapes) · [Lab](level-3-code-labs.md#q8-shape-cache)

## Q9. Who owns request lifecycle versus device execution?
**Problem story:** A dispatcher assigns work to several workshops. A customer may cancel while a workshop is still finishing, and a workshop may restart and deliver an old result late. Unless exactly one place owns the job's current state, the system can publish stale output or release the same resources twice.

**Philosophy:** one engine core owns scheduling state; workers execute explicit plans and return results. **Warning:** stale results require generation fencing and idempotent cancellation. [Deep dive](level-2-internals.md#q9-engine-ownership) · [Lab](level-3-code-labs.md#q9-fenced-worker)

## Q10. How do streaming and cancellation stay bounded?
**Problem story:** A producer emits pieces faster than a client can read them. The waiting pile grows while the client may disconnect at any moment. If only the network connection is closed but the factory keeps producing and reserving materials, an invisible abandoned job consumes the system.

**Philosophy:** bound every queue and propagate cancellation through output, scheduler, and KV ownership. **Warning:** an HTTP disconnect alone may leak live engine work. [Deep dive](level-2-internals.md#q10-streaming-and-cancellation) · [Lab](level-3-code-labs.md#q10-bounded-stream)
