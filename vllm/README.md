# vLLM Technology Radar

[Radar home](../README.md)

Source baseline: [vLLM `v0.32.0`](https://github.com/vllm-project/vllm/tree/5df63a7203cdb9328d824a27b682e77c7b9928be), commit `5df63a7203cdb9328d824a27b682e77c7b9928be`.

## Reading paths

- [Level 1](level-1-philosophy.md) — philosophy and recognition
- [Level 2](level-2-internals.md) — internals and interview follow-ups
- [Level 3](level-3-code-labs.md) — implementation labs

## Core problem families

1. KV-cache fragmentation and PagedAttention
2. Continuous batching and iteration-level scheduling
3. Prefill/decode interference and chunked prefill
4. Memory admission control and request preemption
5. Prefix caching and reusable computation
6. Tensor, pipeline, data, and expert parallelism
7. Model loading, quantization, and memory layout
8. Speculative decoding
9. Distributed execution and worker coordination
10. Streaming output, cancellation, and backpressure
11. Throughput/latency benchmarking and capacity planning
12. Failure isolation and production observability

## Three-level contract

- `level-1-philosophy.md`: problem recognition and system-design philosophy
- `level-2-internals.md`: execution workflow, scheduler logic, trade-offs, and interview follow-ups
- `level-3-code-labs.md`: simplified schedulers, cache allocators, batching simulations, and implementation exercises
