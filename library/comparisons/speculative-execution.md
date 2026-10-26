# Speculative Execution and Control

[Comparisons](README.md) · [vLLM question](../../vllm/level-1-philosophy.md#q6-how-can-cheap-predictions-reduce-calls-to-an-expensive-model) · [SGLang question](../../sglang/level-1-philosophy.md#q7-how-far-ahead-should-a-cheaper-predictor-be-allowed-to-work)

## Common problem

An inexpensive predictor can propose future tokens. The target model can verify several proposals together. Only verified tokens may enter the response or persistent request state.

## Same correctness, different control question

Both systems need distribution-preserving acceptance and rollback of rejected state. vLLM's question emphasizes the speculate-and-verify data path and its proposer choices. SGLang's question emphasizes how the runtime changes proposal depth as acceptance and resource pressure change.

The difference is complementary, not competitive. Verification is the correctness mechanism. Adaptive depth is a control policy above that mechanism.

## What to measure

Acceptance rate alone is insufficient. Measure accepted tokens per target step, proposer time, verification time, extra memory, inter-token latency, and tail behavior. A controller should optimize net saved target cost and use hysteresis to avoid oscillation.
