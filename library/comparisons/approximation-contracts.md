# Approximation Contracts

[Comparisons](README.md) · [Redis approximation](../../redis/level-1-philosophy.md#q4-when-is-an-approximate-answer-the-correct-engineering-answer) · [FAISS quality budget](../../faiss/level-1-philosophy.md#q2-how-should-a-service-budget-recall-latency-and-bytes-per-vector) · [ONNX Runtime quantization](../../onnxruntime/level-1-philosophy.md#q9-when-is-reduced-numerical-precision-an-acceptable-execution-plan)

## Common problem

Exact work or representation exceeds a latency, memory, or throughput budget. Each system intentionally permits error, but only inside a measurable contract.

| Dimension | Redis | FAISS | ONNX Runtime |
|---|---|---|---|
| Oracle | Exact count or complete candidate policy | Exact flat top-k search | Full-precision model on an evaluation corpus |
| Error unit | Cardinality or eviction-choice error | Missing true neighbors and rank changes | Task-metric loss and per-output numerical error |
| Resource saved | Metadata, memory, and per-operation work | Distance computations, bandwidth, and vector bytes | Weight/activation bytes and hardware execution cost |
| Control | Sketch size or sample count | `nprobe`, `efSearch`, code size, and reranking depth | Bit width, calibration, per-channel choice, and excluded nodes |
| Dangerous input | Skew or adversarial access distribution | Drift, sparse cohorts, or boundary neighbors | Calibration drift, outliers, and sensitive operations |

## Why the difference matters

“Approximate” does not describe one reusable accuracy number. A sketch has aggregate statistical error. ANN retrieval omits or reorders neighbors. Quantization perturbs values and can change a model decision. The transferable workflow is the same: keep an oracle, state the loss function, test realistic tails, and bind knobs to a resource envelope. The product consequence of error remains domain-specific.
