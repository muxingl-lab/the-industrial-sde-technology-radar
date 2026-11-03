# Atomic Generation Replacement

[Comparisons](README.md) · [Redis AOF rewrite](../../redis/level-1-philosophy.md#q9-how-do-you-keep-an-append-only-history-from-growing-forever) · [FAISS index publication](../../faiss/level-1-philosophy.md#q8-how-should-a-serving-system-replace-a-rebuilt-index-without-exposing-a-partial-generation)

## Common problem

Large authoritative state must be rebuilt while readers and writes continue. Editing the live artifact exposes partial state, so both designs construct a replacement and switch generations.

| Dimension | Redis AOF | FAISS serving index |
|---|---|---|
| Artifact | Compact command history | Serialized trained index plus metadata and ID mapping |
| Concurrent change | Buffered commands during rewrite | New corpus changes require a delta policy or a later generation |
| Validation | Writable file, format, and persistence checks | Reload, checksum, embedding contract, and recall smoke tests |
| Switch | Atomic file/generation replacement | Atomic manifest or in-process pointer publication |
| Reader retirement | Persistence process/file lifecycle | Reference counting, epochs, or request draining |

## Why the difference matters

The atomic switch is only the final step. Redis must preserve writes acknowledged during the rewrite. A FAISS library object has no universal mutation log, so the surrounding service must define whether builds use a snapshot, replay deltas, or accept a freshness cutoff. Reusing the pattern requires naming what happens between the build snapshot and publication.
