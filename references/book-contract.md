# Book Contract

## Question identity

A core question names a reusable engineering decision, for example:

- “How do you keep variable-length state from fragmenting accelerator memory?”
- “How should a scheduler combine requests with different execution phases?”

Avoid product-trivia headings such as “What does `FooManager` do?” A class or function belongs in the implementation evidence, not in the durable question identity.

## Level 1 contract

Answer in roughly four parts:

1. **Philosophy:** the general principle.
2. **Think of:** neighboring standard patterns and systems.
3. **System example:** where the pinned source applies it.
4. **Warning:** the dominant limitation or failure mode.

The reader should be able to recognize the problem family after 30–60 seconds.

## Level 2 contract

Cover:

- triggering workload and constraints;
- end-to-end control/data flow;
- state and resource ownership;
- invariants and lifecycle transitions;
- complexity and important constant factors;
- overload, cancellation, failure, and recovery;
- observability and capacity signals where relevant;
- comparison with plausible alternatives;
- interview follow-ups with direct answers.

This level should be sufficient for a senior-SDE design or source-discussion interview without requiring Level 3.

## Level 3 contract

Choose the smallest code that exposes the mechanism. Include:

- types representing the important state;
- transition or scheduling logic;
- assertions or explicit invariants;
- a handwritten extension;
- a meaningful correctness, fault, or performance test.

Use the language that best exposes the mechanism. Prefer readable Java/Python for algorithms; use C/C++/CUDA-style pseudocode where memory layout, atomics, kernels, or OS primitives are the lesson.

## Navigation contract

- Each file links to the radar home and service home.
- Every numbered question has links to the same question at the other two levels.
- Number, anchor, and conceptual scope stay aligned.
- Service README states the release tag, commit, and source repository.
