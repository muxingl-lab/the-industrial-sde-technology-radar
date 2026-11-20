# Temporal Correctness

[Comparisons](README.md) · [Feast point-in-time join](../../feast/level-1-philosophy.md#q1-how-can-training-reconstruct-only-what-was-knowable-at-each-historical-decision-time) · [Flink event-time progress](../../flink/level-1-philosophy.md#q1-how-can-a-system-make-time-based-decisions-when-records-arrive-out-of-order)

## Common problem

A result depends on what was knowable at a particular time, but data arrives late and storage or computation observes it later. Using the newest visible value leaks future information into the decision.

| Dimension | Feast historical retrieval | Flink event-time computation |
|---|---|---|
| Decision time | Timestamp of each historical entity row | Current operator event-time frontier |
| Evidence boundary | Latest feature event at or before that row | Minimum watermark across active inputs |
| Primary operation | Offline as-of join | Online progress and timer firing |
| Late information | Rebuilding training data can include it if valid then | May correct an open window or enter a late-data path |
| Liveness problem | Query cost and bounded feature history | A silent or slow input can stop progress |

## Why the difference matters

Both reject processing-time visibility as the definition of truth. Feast asks a retrospective question over stored histories: “what value was valid at this past decision?” Flink asks a live question with incomplete evidence: “how far may computation advance now?” That distinction is fundamental. An as-of join can inspect the history already stored; a watermark must trade latency against the risk of future late arrival. The reusable lesson is to name decision time, evidence time, and correction policy separately.
