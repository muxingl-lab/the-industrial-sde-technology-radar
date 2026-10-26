# Prefix Reuse: Hashed Blocks vs. Radix Paths

[Comparisons](README.md) · [vLLM question](../../vllm/level-1-philosophy.md#q4-when-is-prefix-computation-safely-reusable) · [SGLang question](../../sglang/level-1-philosophy.md#q1-how-can-the-server-find-the-longest-shared-beginning-between-requests)

## Common problem

Requests repeat long prefixes whose intermediate model state is expensive to recompute. Reuse must find the longest valid match and keep shared memory alive without crossing model, adapter, modality, or tenant boundaries.

## Two indexes for the same reuse opportunity

vLLM hashes full blocks and chains each block's identity to its parent. Lookup naturally follows block boundaries and works like content-addressed storage. SGLang stores token paths in a compressed radix tree. Lookup naturally exposes branching structure and partial path relationships.

This is more than a naming difference. The block hash makes identity, distribution, and equality cheap, but reuse is block-aligned. The radix tree makes longest-prefix structure explicit and supports path splitting, but mutation, eviction, and reference propagation become tree operations.

## Selection rule

Prefer content-addressed blocks when immutable block identity and block-granular allocation dominate. Prefer an explicit prefix tree when prefix branching, longest-match traversal, and cache-aware scheduling need first-class structure. Both still require a complete semantic cache key.

