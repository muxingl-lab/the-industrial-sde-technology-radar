# SGLang — Level 1: Philosophy

[Radar](../README.md) · [SGLang](README.md) · [Level 2](level-2-internals.md) · [Level 3](level-3-code-labs.md)

## Q1. How is the longest reusable prefix found across evolving requests?
**Problem story:** A help desk receives many conversations that begin with the same company manual, then branch into department rules and finally a customer's question. Reusing only an entire conversation misses most sharing. Comparing every new request with every old request is too slow. We need to find the longest shared beginning and remember where branches diverge.

**Philosophy:** index computation by structural prefix, not whole-request equality. RadixAttention maps radix-tree paths to KV locations. **Warning:** node splits, eviction, and reference state must preserve ownership. [Deep dive](level-2-internals.md#q1-radix-prefix-cache) · [Lab](level-3-code-labs.md#q1-radix-prefix-cache)

## Q2. How are asynchronous requests continuously batched?
**Problem story:** Work arrives while the machine is already busy. Every job alternates between stages of very different sizes, and jobs finish at different moments. Fixed groups leave empty seats when one member finishes. We need to refill the machine continuously while retaining a clear lifecycle for every job.

**Philosophy:** batching is an online state machine over waiting, prefill, decode, retraction, and completion. **Warning:** utilization, fairness, TTFT, and ITL conflict. [Deep dive](level-2-internals.md#q2-continuous-scheduling) · [Lab](level-3-code-labs.md#q2-request-scheduler)

## Q3. How do large prefills share iterations with decode?
**Problem story:** Some customers arrive with a book that must be read before answering; others are already in a conversation and need one quick next word. Always reading whole books first makes active conversations feel frozen. Always favoring quick answers means large books may never start.

**Philosophy:** budget phases independently and chunk monopolizing work. **Warning:** more boundaries increase metadata and may weaken kernels. [Deep dive](level-2-internals.md#q3-chunked-prefill) · [Lab](level-3-code-labs.md#q3-prefill-controller)

## Q4. How should KV state span GPU, host, and storage?
**Problem story:** A worker has a tiny desk, a larger cabinet across the room, and a warehouse across town. Keeping everything on the desk is impossible; fetching from the warehouse may be slower than recreating the item. Placement must consider both the chance of reuse and the real retrieval cost.

**Philosophy:** tier by reuse probability versus transfer and recomputation cost. HiCache forms a KV hierarchy. **Warning:** a slow-tier hit can cost more than recomputation. [Deep dive](level-2-internals.md#q4-hierarchical-cache) · [Lab](level-3-code-labs.md#q4-tiered-cache)

## Q5. When should prefill and decode use separate fleets?
**Problem story:** One stage of a job needs powerful burst computation; the next needs repeated access to a large working set. A single general-purpose team is easy to coordinate but poorly matched to both stages. Specialized teams help only if the handoff is reliable and cheaper than the saved work.

**Philosophy:** disaggregate phases with different resource profiles and make KV transfer a first-class protocol. **Warning:** transfer, staging, routing, and partial failure can dominate. [Deep dive](level-2-internals.md#q5-pd-disaggregation) · [Lab](level-3-code-labs.md#q5-kv-transfer)

## Q6. How is schema-conforming output guaranteed?
**Problem story:** A machine writes a legal form one symbol at a time. Checking the finished form and rejecting it wastes the entire run. We want to prevent any next symbol that would make a valid completion impossible, even though one machine token may contain several characters or part of a character.

**Philosophy:** intersect next-token choices with a formal-language state machine; jump deterministic spans when safe. **Warning:** token boundaries make character-level reasoning insufficient. [Deep dive](level-2-internals.md#q6-constrained-decoding) · [Lab](level-3-code-labs.md#q6-grammar-mask)

## Q7. How should speculation depth adapt?
**Problem story:** An assistant drafts several steps ahead for a reviewer. On easy text, long drafts save time; on difficult text, most drafts are discarded. A fixed number of speculative steps is inevitably wrong for some passages, so the system must learn when to be bold and when to stop early.

**Philosophy:** treat depth as a feedback-controlled variable based on accepted work and resource pressure. **Warning:** average acceptance can hide tail-latency harm. [Deep dive](level-2-internals.md#q7-adaptive-speculation) · [Lab](level-3-code-labs.md#q7-speculation-controller)

## Q8. How should replicas be selected when both load and cache locality matter?
**Problem story:** Several service desks can answer a request. One has the relevant files open but a long line; another is idle but must reload everything. Sending everyone to the warm desk creates a hotspot, while always choosing the shortest line repeatedly throws away useful preparation.

**Philosophy:** price queueing and reusable state together. **Warning:** stale metadata causes hotspots and oscillation. [Deep dive](level-2-internals.md#q8-routing-and-parallelism) · [Lab](level-3-code-labs.md#q8-locality-router)

## Q9. How do tokens map safely to physical KV slots?
**Problem story:** Thousands of travelers use lockers, leave, return, and sometimes share stored material. Locker numbers are reused. If an old claim ticket points to a locker reassigned to someone else, data crosses customer boundaries. We need authoritative ownership and safe reuse of physical slots.

**Philosophy:** separate request/token identity from physical slots with authoritative allocation metadata. **Warning:** stale mappings cause cross-request corruption. [Deep dive](level-2-internals.md#q9-memory-pool-indirection) · [Lab](level-3-code-labs.md#q9-token-slot-pool)

## Q10. How does a multi-process serving pipeline preserve ownership?
**Problem story:** A request passes through translators, planners, factory workers, and a delivery desk. Each stage runs at a different speed and may restart. If queues are unbounded or cancellation stops at only one stage, obsolete work continues downstream and eventually overwhelms the pipeline.

**Philosophy:** each stage owns one responsibility and communicates through bounded typed protocols. **Warning:** cancellation must cross tokenizer, scheduler, workers, detokenizer, and output. [Deep dive](level-2-internals.md#q10-serving-pipeline) · [Lab](level-3-code-labs.md#q10-fenced-pipeline)
