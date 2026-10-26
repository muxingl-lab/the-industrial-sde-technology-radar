# SGLang — Level 1: Philosophy

[Radar](../README.md) · [SGLang](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

## Q1. How is the longest reusable prefix found across evolving requests?
**Philosophy:** index computation by structural prefix, not whole-request equality. RadixAttention maps radix-tree paths to KV locations. **Warning:** node splits, eviction, and reference state must preserve ownership. [Deep dive](level-2-internals.md#q1-radix-prefix-cache) · [Lab](level-3-code-labs.md#q1-radix-prefix-cache)

## Q2. How are asynchronous requests continuously batched?
**Philosophy:** batching is an online state machine over waiting, prefill, decode, retraction, and completion. **Warning:** utilization, fairness, TTFT, and ITL conflict. [Deep dive](level-2-internals.md#q2-continuous-scheduling) · [Lab](level-3-code-labs.md#q2-request-scheduler)

## Q3. How do large prefills share iterations with decode?
**Philosophy:** budget phases independently and chunk monopolizing work. **Warning:** more boundaries increase metadata and may weaken kernels. [Deep dive](level-2-internals.md#q3-chunked-prefill) · [Lab](level-3-code-labs.md#q3-prefill-controller)

## Q4. How should KV state span GPU, host, and storage?
**Philosophy:** tier by reuse probability versus transfer and recomputation cost. HiCache forms a KV hierarchy. **Warning:** a slow-tier hit can cost more than recomputation. [Deep dive](level-2-internals.md#q4-hierarchical-cache) · [Lab](level-3-code-labs.md#q4-tiered-cache)

## Q5. When should prefill and decode use separate fleets?
**Philosophy:** disaggregate phases with different resource profiles and make KV transfer a first-class protocol. **Warning:** transfer, staging, routing, and partial failure can dominate. [Deep dive](level-2-internals.md#q5-pd-disaggregation) · [Lab](level-3-code-labs.md#q5-kv-transfer)

## Q6. How is schema-conforming output guaranteed?
**Philosophy:** intersect next-token choices with a formal-language state machine; jump deterministic spans when safe. **Warning:** token boundaries make character-level reasoning insufficient. [Deep dive](level-2-internals.md#q6-constrained-decoding) · [Lab](level-3-code-labs.md#q6-grammar-mask)

## Q7. How should speculation depth adapt?
**Philosophy:** treat depth as a feedback-controlled variable based on accepted work and resource pressure. **Warning:** average acceptance can hide tail-latency harm. [Deep dive](level-2-internals.md#q7-adaptive-speculation) · [Lab](level-3-code-labs.md#q7-speculation-controller)

## Q8. How should replicas be selected when both load and cache locality matter?
**Philosophy:** price queueing and reusable state together. **Warning:** stale metadata causes hotspots and oscillation. [Deep dive](level-2-internals.md#q8-routing-and-parallelism) · [Lab](level-3-code-labs.md#q8-locality-router)

## Q9. How do tokens map safely to physical KV slots?
**Philosophy:** separate request/token identity from physical slots with authoritative allocation metadata. **Warning:** stale mappings cause cross-request corruption. [Deep dive](level-2-internals.md#q9-memory-pool-indirection) · [Lab](level-3-code-labs.md#q9-token-slot-pool)

## Q10. How does a multi-process serving pipeline preserve ownership?
**Philosophy:** each stage owns one responsibility and communicates through bounded typed protocols. **Warning:** cancellation must cross tokenizer, scheduler, workers, detokenizer, and output. [Deep dive](level-2-internals.md#q10-serving-pipeline) · [Lab](level-3-code-labs.md#q10-fenced-pipeline)
