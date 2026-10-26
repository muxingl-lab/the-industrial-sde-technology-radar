# vLLM Technology Radar

[Radar home](../README.md)

This service volume will study vLLM as a source-code case study in high-throughput LLM inference.

## Planned core problem families

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

The three level files will be added when this service becomes the active source-study volume.
