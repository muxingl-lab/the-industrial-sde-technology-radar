# Overload and Backpressure

[Comparisons](README.md) · [Redis slow consumers](../../redis/level-1-philosophy.md#q11-what-should-happen-when-a-consumer-is-slower-than-a-producer) · [vLLM memory admission](../../vllm/level-1-philosophy.md#q5-what-happens-when-active-requests-need-more-accelerator-memory-than-exists) · [vLLM streaming](../../vllm/level-1-philosophy.md#q10-how-do-streaming-and-cancellation-stay-bounded) · [SGLang pipeline](../../sglang/level-1-philosophy.md#q10-how-does-a-multi-process-serving-pipeline-preserve-ownership)

## Common problem

One stage accepts or produces work faster than the next stage can hold or consume it. Unlimited buffering delays the decision until the process fails.

## Different scarce resources

Redis protects host memory from client output buffers. vLLM admission protects accelerator memory before scheduling more tokens; its streaming path also protects host queues after execution. SGLang must bound several inter-process stages, so pressure may appear far from the original request.

This is a fundamental difference in where overload becomes irreversible. An output buffer can often drop a client after work has completed. Accelerator admission must reject or defer work before allocation. A multi-stage pipeline must propagate pressure upstream or it merely moves the queue.

## Required policy

Every boundary needs a capacity unit, a soft or hard limit, an overload action, and an observable age or debt metric. State explicitly whether the system slows producers, rejects new work, preempts existing work, drops output, spills to another tier, or disconnects consumers.
