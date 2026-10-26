# Book Contract

## Question identity

A core question names a reusable engineering decision, for example:

- “How do you keep variable-length state from fragmenting accelerator memory?”
- “How should a scheduler combine requests with different execution phases?”

Avoid product-trivia headings such as “What does `FooManager` do?” A class or function belongs in the implementation evidence, not in the durable question identity.

## Level 1 contract

Level 1 starts with a **technical problem context**. It may be long. Assume general SDE knowledge—requests, processes, threads, queues, memory allocation, CPU/GPU execution, network calls, caches, and failures—but not specialized knowledge of the featured system. Explain the initial workflow, what changes at scale, the observed failure, the scarce resource, the desired outcome, and why the obvious fix is insufficient. Introduce specialized vocabulary only after the conflict is understood.

A strong prompt passes the domain-outsider test: an SDE with systems fundamentals but no Redis, vLLM, or SGLang experience can explain the problem before reading the answer. Avoid undefined terms such as “KV cache,” “prefill,” “decode,” “radix attention,” or internal class names in the initial framing. Do not replace the system with a restaurant, warehouse, library, or other extended everyday-life analogy; a short analogy may clarify an already defined technical problem, but cannot define it.

Then answer in roughly five parts:

1. **Technical problem context:** a self-contained workflow, scale transition, failure, and failed obvious approach.
2. **Philosophy:** the general principle.
3. **Think of:** neighboring standard patterns and systems.
4. **System example:** where the pinned source applies it.
5. **Warning:** the dominant limitation or failure mode.

The reader should be able to recognize the problem family after 30–60 seconds and should never need Level 2 to understand the question itself.

### Technical-context checklist

- Can a generalist SDE understand every noun without a domain-specific glossary?
- Is the request/memory/execution workflow concrete and long enough to establish causality?
- Is the naive solution stated, along with why it becomes wasteful or unsafe?
- Is the tension explicit—for example memory versus flexibility, throughput versus latency, or reuse versus correctness?
- Does the story stop before giving away the solution?
- Could the same story plausibly occur in another system?

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
