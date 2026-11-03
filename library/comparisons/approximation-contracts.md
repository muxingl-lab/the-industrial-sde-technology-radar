# Approximation Contracts

[Comparisons](README.md) · [Redis approximation](../../redis/level-1-philosophy.md#q4-when-is-an-approximate-answer-the-correct-engineering-answer) · [FAISS quality budget](../../faiss/level-1-philosophy.md#q2-how-should-a-service-budget-recall-latency-and-bytes-per-vector)

## Common problem

Exact work exceeds a latency, memory, or throughput budget. Both systems intentionally permit error, but only inside a measurable contract.

| Dimension | Redis | FAISS |
|---|---|---|
| Oracle | Exact count or complete candidate policy | Exact flat top-k search |
| Error unit | Cardinality or eviction-choice error | Missing true neighbors and rank changes |
| Resource saved | Metadata, memory, and per-operation work | Distance computations, memory bandwidth, and vector bytes |
| Control | Sketch size or sample count | `nprobe`, `efSearch`, code size, and reranking depth |
| Dangerous input | Skew or adversarial access distribution | Query/data drift, sparse cohorts, or boundary neighbors |

## Why the difference matters

“Approximate” does not describe one reusable accuracy number. A HyperLogLog estimate has a statistical aggregate error; ANN retrieval has a set- and rank-dependent omission error. The transferable workflow is the same—keep an oracle, state the loss function, benchmark realistic tails, and bind knobs to a resource envelope—but the product consequence of an error must be defined separately.
