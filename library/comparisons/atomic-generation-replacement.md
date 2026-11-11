# Atomic Generation Replacement

[Comparisons](README.md) · [Redis AOF rewrite](../../redis/level-1-philosophy.md#q9-how-do-you-keep-an-append-only-history-from-growing-forever) · [FAISS index publication](../../faiss/level-1-philosophy.md#q8-how-should-a-serving-system-replace-a-rebuilt-index-without-exposing-a-partial-generation) · [ONNX Runtime session publication](../../onnxruntime/level-1-philosophy.md#q10-how-should-a-service-keep-model-preparation-off-the-first-live-request)

## Common problem

Large authoritative state must be rebuilt while readers and writes continue. Editing the live artifact exposes partial state, so both designs construct a replacement and switch generations.

| Dimension | Redis AOF | FAISS serving index | ONNX Runtime session |
|---|---|---|---|
| Artifact | Compact command history | Serialized trained index plus metadata and ID mapping | Model/ORT artifact, weights, provider context, and runtime manifest |
| Concurrent change | Buffered commands during rewrite | Corpus changes require a delta policy or later generation | Model is immutable; live requests remain on the old session |
| Validation | Format and persistence checks | Reload, checksum, embedding contract, and recall tests | Compatibility, load, warmup, numerical, and provider-placement tests |
| Switch | Atomic file/generation replacement | Atomic manifest or process pointer | Atomic ready-session pointer or traffic generation |
| Reader retirement | Persistence process/file lifecycle | Reference counting, epochs, or request draining | Request draining followed by session and device-memory release |

## Why the difference matters

The atomic switch is only the final step. Redis must preserve writes acknowledged during rewrite. A FAISS service must define how corpus changes cross the build window. An ONNX Runtime service activates an immutable model, but host-specific compilation, weight transfer, and warmup mean “artifact present” is not “session ready.” Reusing the pattern requires a precise readiness boundary before publication.
