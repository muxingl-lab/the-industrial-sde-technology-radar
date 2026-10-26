---
name: build-industrial-sde-radar
description: Build or extend a source-driven Industrial SDE Technology Radar volume with linked philosophy, interview-internals, and implementation-code levels. Use for adding systems such as databases, runtimes, inference engines, or distributed services to this repository; not for generic tutorials that do not require source evidence and transferable problem-solving patterns.
metadata:
  short-description: Build source-driven SDE radar volumes
---

# Build the Industrial SDE Technology Radar

Produce a durable map from production problem shapes to standard engineering patterns. Treat a named system as a source-code case study, not as the book's organizing principle.

## Required outcome

Each service folder must have:

- `README.md`: pinned source version, scope, and links to all depths;
- `level-1-philosophy.md`: problem recognition, foundational questions, pattern, and principal warning;
- `level-2-internals.md`: end-to-end workflow, invariants, trade-offs, failure modes, and interview follow-ups;
- `level-3-code-labs.md`: mechanism-sized code or pseudocode, handwritten exercises, and meaningful tests.

Every core question must link Level 1 → Level 2 → Level 3 and back. Keep question numbering and meaning identical across levels.

## Workflow

1. Pin an official release tag and commit. Prefer upstream source and official design documentation over commentary.
2. Map entry points, control flow, state ownership, scheduling, memory/data structures, distributed boundaries, recovery paths, and observability.
3. Extract transferable problem families. Merge source features that teach the same pattern; split features when their invariants differ.
4. Write Level 1 first to test whether each question represents a reusable decision rather than product trivia.
5. Write Level 2 from verified workflows and source evidence. Include the follow-ups needed to expose shallow understanding.
6. Write Level 3 around the smallest implementation that makes the invariant concrete. Do not present toy code as production-ready.
7. Run `python3 scripts/validate_radar.py .` and the skill validator before delivery.

Read [references/source-study.md](references/source-study.md) when researching a new system. Read [references/book-contract.md](references/book-contract.md) when adding or restructuring a volume.

## Quality boundary

- Explain why the mechanism exists before how it works.
- Separate algorithmic complexity from cache, allocation, synchronization, I/O, and tail-latency costs.
- State the authoritative owner and consistency boundary for every mutable workflow.
- Distinguish foreground latency from total/background resource cost.
- For approximation, define the tolerated error and business loss.
- For recovery, identify identity/epoch, progress position, retained history, and full-rebuild fallback.
- For concurrency, state ownership, handoff, cancellation, backpressure, and stale-completion handling.
- For distributed decisions, distinguish observation, suspicion, agreement, authority, and fencing.
- Do not claim completeness from filenames alone. Verify the active implementation path for the pinned version.
- Use stable commit-pinned source links where practical. Clearly mark inference rather than presenting it as source fact.
