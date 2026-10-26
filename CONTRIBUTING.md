# Contributing to the Industrial SDE Technology Radar

This project has two indexes: services and problems. A contribution is incomplete if it updates only one.

## Before you write

1. Pin the official release and commit you will study.
2. Read the active source path, tests, and official design notes.
3. Search [the problem library](library/README.md) by problem, scarce resource, invariant, and pattern—not only by product terminology.
4. Read any related chapter in [cross-system comparisons](library/comparisons/README.md).

## Decide whether the problem is new

Use the same question when the triggering failure and core invariant are the same, even if the products use different names. Create a new question when the reader must make a materially different decision.

Classify overlap before drafting:

| Classification | Meaning | Required action |
|---|---|---|
| Same mechanism | The systems differ mainly in names or implementation language | Share one pattern and explain implementation details in a comparison |
| Same problem, different constraints | The desired outcome matches, but resource units, ownership, or workload differ | Create or expand a comparison chapter; this is usually the most valuable case |
| Neighboring problem | The mechanisms look similar, but correctness or lifecycle differs | Cross-link them and state the boundary explicitly |
| No meaningful overlap | The problem and invariant are distinct | Add only the library row |

## Add a service question

1. Add the same numbered question to all three levels.
2. Write Level 1 as `Starting point → What breaks → The question` before naming the solution.
3. Cover workflow, ownership, invariants, failure, and follow-ups in Level 2.
4. Add mechanism-sized code, a handwritten extension, and a meaningful test in Level 3.
5. Add one row to `library/README.md`. A row always represents exactly one service and one problem.
6. Link the question to every relevant comparison chapter.
7. Update or create a comparison when another service solves the same pattern.

## Write a comparison chapter

A comparison is not a feature table. It must answer:

1. What common failure leads both systems to the pattern?
2. What unit does each system schedule, allocate, cache, or own?
3. Which invariant is the same?
4. Which constraint changes the implementation?
5. Is the difference superficial, operational, or fundamental?
6. Under what workload would one design fail or become a poor fit?

Keep comparisons independent from service chapters. Link to pinned source evidence and back to each service question.

## Validate

Run:

```bash
python3 scripts/validate_radar.py .
git diff --check
```

Before submitting, read the prose at speaking pace. Remove undefined terms, fused sentences, repeated conclusions, and claims that lack source evidence.

