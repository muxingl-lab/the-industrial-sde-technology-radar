# SGLang — Level 1: Philosophy

[Radar](../README.md) · [SGLang](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

## Q1. How can the server find the longest shared beginning between requests?
**Starting point.** Requests often share a system prompt, a document, or an earlier conversation. They may match for thousands of tokens before diverging at different positions.

**What breaks.** Caching only complete prompts misses most of this overlap. Comparing each new request with every cached request becomes too expensive as the cache grows. The index also changes while active requests share entries and old entries are evicted.

**The question.** How can the runtime find the longest cached prefix, represent its branches compactly, and keep the corresponding device memory alive for exactly as long as it is needed?

**Philosophy:** index computation by structural prefix, not whole-request equality. RadixAttention maps radix-tree paths to KV locations. **Warning:** node splits, eviction, and reference state must preserve ownership. [Deep dive](level-2-internals.md#q1-radix-prefix-cache) · [Lab](level-3-code-labs.md#q1-radix-prefix-cache)

## Q2. How are asynchronous requests continuously batched?
**Starting point.** Requests arrive asynchronously. They have different input and output lengths, and their work changes from processing many input tokens to generating one token at a time.

**What breaks.** A fixed batch loses capacity as requests finish. Rebuilding the batch improves utilization, but every rebuild touches request state, memory reservations, cached prefixes, cancellation, and output.

**The question.** What request lifecycle lets the scheduler change batch membership every iteration without losing, duplicating, or prematurely freeing work?

**Philosophy:** batching is an online state machine over waiting, prefill, decode, retraction, and completion. **Warning:** utilization, fairness, TTFT, and ITL conflict. [Deep dive](level-2-internals.md#q2-continuous-scheduling) · [Lab](level-3-code-labs.md#q2-request-scheduler)

## Q3. How can long inputs share the GPU with active output streams?
**Starting point.** A long input may require thousands of token computations before its first output. Existing streams need small, frequent steps to keep returning tokens.

**What breaks.** Running the long input as one unit freezes active streams. Always serving active streams can starve new requests. Dividing work into very small pieces reduces GPU efficiency.

**The question.** How should the scheduler size and admit input chunks under token and memory budgets while protecting both first-token and inter-token latency?

**Philosophy:** budget phases independently and chunk monopolizing work. **Warning:** more boundaries increase metadata and may weaken kernels. [Deep dive](level-2-internals.md#q3-chunked-prefill) · [Lab](level-3-code-labs.md#q3-prefill-controller)

## Q4. How should reusable model state move across GPU, host memory, and storage?
**Starting point.** Reusable model state can avoid substantial computation, but accelerator memory is small. Host memory is larger but requires a transfer. External storage is larger again and slower.

**What breaks.** Keeping too much cached state on the accelerator blocks active requests. Moving everything away saves device memory but can make retrieval slower than recomputation. Asynchronous movement also creates periods when a block exists but is not ready to use.

**The question.** Which state belongs in each tier, and how should the runtime compare reuse value, transfer cost, recomputation cost, and incomplete transfers?

**Philosophy:** tier by reuse probability versus transfer and recomputation cost. HiCache forms a KV hierarchy. **Warning:** a slow-tier hit can cost more than recomputation. [Deep dive](level-2-internals.md#q4-hierarchical-cache) · [Lab](level-3-code-labs.md#q4-tiered-cache)

## Q5. When should input processing and token generation use separate worker fleets?
**Starting point.** Processing a request's input performs a large amount of parallel computation. Generating later tokens performs smaller steps that repeatedly read a growing body of state. The two phases use hardware differently.

**What breaks.** One shared worker fleet is easy to operate but may be poorly matched to both phases. Separate fleets can scale independently, but the first fleet must transfer intermediate state before the second can continue.

**The question.** When does specialization repay the network handoff, and what protocol makes that handoff correct under retries, timeouts, and worker failure?

**Philosophy:** disaggregate phases with different resource profiles and make KV transfer a first-class protocol. **Warning:** transfer, staging, routing, and partial failure can dominate. [Deep dive](level-2-internals.md#q5-pd-disaggregation) · [Lab](level-3-code-labs.md#q5-kv-transfer)

## Q6. How is schema-conforming output guaranteed?
**Starting point.** Many applications need valid JSON or text that follows a schema. The model still generates one token at a time, and a token may contain several characters, part of a character, or punctuation mixed with text.

**What breaks.** Validating only after generation wastes the entire request when the output is malformed. Applying character-level rules directly to tokens rejects valid choices or permits invalid ones.

**The question.** How can the server track grammar state, determine which tokens preserve at least one valid completion, and skip deterministic spans without changing the result?

**Philosophy:** intersect next-token choices with a formal-language state machine; jump deterministic spans when safe. **Warning:** token boundaries make character-level reasoning insufficient. [Deep dive](level-2-internals.md#q6-constrained-decoding) · [Lab](level-3-code-labs.md#q6-grammar-mask)

## Q7. How far ahead should a cheaper predictor be allowed to work?
**Starting point.** A cheaper component can propose several future tokens before the target model verifies them. Acceptance varies by request and by position within one response.

**What breaks.** A fixed proposal length wastes opportunity on easy text and wastes computation on difficult text. Reacting too quickly to recent results makes the proposal length oscillate.

**The question.** Which signals should control speculation depth, and how can the controller improve saved target-model time without damaging tail latency or memory pressure?

**Philosophy:** treat depth as a feedback-controlled variable based on accepted work and resource pressure. **Warning:** average acceptance can hide tail-latency harm. [Deep dive](level-2-internals.md#q7-adaptive-speculation) · [Lab](level-3-code-labs.md#q7-speculation-controller)

## Q8. How should replicas be selected when both load and cache locality matter?
**Starting point.** Several replicas can execute the same request. One may already hold most of the reusable prefix; another may have a much shorter queue.

**What breaks.** Routing only to the shortest queue repeats cached computation. Routing only to the warmest cache creates hotspots. Both load and cache reports arrive late, so many routers may make the same outdated choice at once.

**The question.** How should routing combine queueing time, reusable work, transfer cost, and stale telemetry without causing oscillation?

**Philosophy:** price queueing and reusable state together. **Warning:** stale metadata causes hotspots and oscillation. [Deep dive](level-2-internals.md#q8-routing-and-parallelism) · [Lab](level-3-code-labs.md#q8-locality-router)

## Q9. How should logical token positions map to reusable physical memory slots?
**Starting point.** The scheduler identifies data by request and token position. Device kernels access fixed physical slots. The runtime constantly allocates, shares, frees, and reuses those slots.

**What breaks.** A stale mapping can make one request read another request's state. A partial allocation failure can leak slots, while an incorrect free can invalidate a shared prefix.

**The question.** Which metadata is authoritative, and how can allocation, sharing, rollback, and reuse update every mapping as one safe lifecycle transition?

**Philosophy:** separate request/token identity from physical slots with authoritative allocation metadata. **Warning:** stale mappings cause cross-request corruption. [Deep dive](level-2-internals.md#q9-memory-pool-indirection) · [Lab](level-3-code-labs.md#q9-token-slot-pool)

## Q10. How does a multi-process serving pipeline preserve ownership?
**Starting point.** One request may pass through tokenization, scheduling, distributed model execution, detokenization, and network streaming. These stages run in different processes and at different speeds.

**What breaks.** Unbounded inter-process queues hide overload until memory is exhausted. Cancellation at one stage leaves obsolete work in the others. After a process restarts, old messages may arrive for a request ID that now means something else.

**The question.** How should stages identify work, bound queues, propagate cancellation, and reject stale messages while preserving throughput?

**Philosophy:** each stage owns one responsibility and communicates through bounded typed protocols. **Warning:** cancellation must cross tokenizer, scheduler, workers, detokenizer, and output. [Deep dive](level-2-internals.md#q10-serving-pipeline) · [Lab](level-3-code-labs.md#q10-fenced-pipeline)
