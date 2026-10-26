# Memory Indirection: vLLM Blocks vs. SGLang Token Slots

[Comparisons](README.md) · [vLLM question](../../vllm/level-1-philosophy.md#q1-how-can-per-request-memory-grow-without-reserving-its-maximum-size) · [SGLang question](../../sglang/level-1-philosophy.md#q9-how-should-logical-token-positions-map-to-reusable-physical-memory-slots)

## Common problem

Logical request positions grow and outlive any one kernel invocation. Physical accelerator memory is fixed, fragmented, and frequently reused. Both systems insert a mapping layer between logical sequence state and physical storage.

## Different unit of reasoning

vLLM presents paging as the central allocation abstraction: requests own or share fixed-size KV blocks, and block tables drive attention. SGLang exposes request-to-token and token-to-KV pool mappings within a larger cache and layout system.

The difference is operational but important. A block allocator reasons about groups of tokens, internal fragmentation, and block-aligned sharing. A slot pool reasons more directly about physical indices, layout-specific pools, and atomic mapping updates. Block size simplifies metadata but coarsens allocation; token-level mapping offers finer control but increases metadata work.

## Shared invariant

No live physical region may have an unintended owner. Allocation failure must roll back every partial mapping. Shared state must remain allocated until the last reference leaves.

