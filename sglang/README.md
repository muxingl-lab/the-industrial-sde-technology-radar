# SGLang Technology Radar

[Radar home](../README.md)

This service volume will study SGLang as a source-code case study in LLM serving, structured generation, and agent workloads.

## Planned core problem families

1. RadixAttention and prefix/KV reuse
2. Request scheduling and continuous batching
3. Prefill/decode disaggregation
4. Structured generation and constrained decoding
5. Tool use and agent execution control
6. Cache-aware routing across replicas
7. Tensor, pipeline, expert, and data parallel execution
8. Speculative decoding and draft-model coordination
9. Multimodal request processing
10. Distributed serving topology and fault handling
11. Streaming, cancellation, and backpressure
12. Benchmarking, observability, and capacity planning

## Three-level contract

- `level-1-philosophy.md`: problem recognition and system-design philosophy
- `level-2-internals.md`: execution workflow, runtime logic, trade-offs, and interview follow-ups
- `level-3-code-labs.md`: radix-cache, scheduler, constrained-decoding, and routing exercises

The three level files will be added when this service becomes the active source-study volume.
