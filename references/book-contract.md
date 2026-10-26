# Book Contract

## Question identity

A core question names a reusable engineering decision, for example:

- “How do you keep variable-length state from fragmenting accelerator memory?”
- “How should a scheduler combine requests with different execution phases?”

Avoid product-trivia headings such as “What does `FooManager` do?” A class or function belongs in the implementation evidence, not in the durable question identity.

## Level 1 contract

Level 1 starts with a **problem story**. It may be long. Prefer an ordinary situation, concrete numbers, or an unfolding failure that a capable engineer can reason about without prior knowledge of the system. Define actors, changing state, scarce resource, desired outcome, and why the obvious solution fails. Introduce domain vocabulary only after the conflict is understood.

A strong prompt passes the outsider test: an SDE unfamiliar with Redis, vLLM, or SGLang can explain the problem in their own words before reading the answer. Avoid undefined terms such as “KV cache,” “prefill,” “decode,” “radix attention,” or internal class names in the initial framing.

Then answer in roughly five parts:

1. **Problem story:** a self-contained situation and the failed obvious approach.
2. **Philosophy:** the general principle.
3. **Think of:** neighboring standard patterns and systems.
4. **System example:** where the pinned source applies it.
5. **Warning:** the dominant limitation or failure mode.

The reader should be able to recognize the problem family after 30–60 seconds and should never need Level 2 to understand the question itself.

### Problem-story checklist

- Can a reader understand every noun without a glossary?
- Is the workload or sequence of events concrete?
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
