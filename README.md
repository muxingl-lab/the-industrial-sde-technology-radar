# The Industrial SDE Technology Radar

This top-level radar trains problem recognition across production systems, not product-name recall.

## Service map

| Service | System category | Status | Entry point |
|---|---|---|---|
| Redis | In-memory data platform | Redis 8.8.3 volume available | [Open Redis](redis/README.md) |
| vLLM | High-throughput LLM inference engine | v0.32.0 volume available | [Open vLLM](vllm/README.md) |
| SGLang | LLM serving and agent runtime | v0.5.22 volume available | [Open SGLang](sglang/README.md) |

Every service uses the same three-depth contract:

| Depth | Purpose | Expected outcome |
|---|---|---|
| Level 1: High-level | Philosophy and decision framing | Recognize the problem family and name the standard pattern |
| Level 2: Interview-level | Workflow, logic, trade-offs, and follow-ups | Handle a complete senior-SDE interview discussion |
| Level 3: Implementation-level | Invariants, pseudocode, and code exercises | Implement the essential mechanism by hand |

Within a service, every core question links directly across all three levels. Level 2 is the default target; Level 1 builds recall and Level 3 turns verbal understanding into engineering ability.

## The five philosophical questions

Ask these before naming a technology:

1. **What is the scarce resource?** CPU, memory, I/O, network, coordination, latency budget, or engineering attention?
2. **What invariant must never be violated?** Ordering, uniqueness, durability, visibility, ownership, or bounded memory?
3. **What can be traded?** Precision, freshness, space, throughput, availability, implementation complexity, or recovery time?
4. **Where can work be moved?** Off the request path, into small increments, to a background worker, to read time, or to recovery time?
5. **How does the mechanism fail?** Under skew, overload, crashes, partitions, long pauses, corrupted input, or operator error?

## Repository contract

```text
radar/
├── README.md
├── redis/
│   ├── README.md
│   ├── level-1-philosophy.md
│   ├── level-2-internals.md
│   └── level-3-code-labs.md
├── vllm/
│   └── ...same depth structure...
└── sglang/
    └── ...same depth structure...
```

Service folders may add `source-map.md`, diagrams, benchmarks, or executable labs, but their three canonical reading levels keep the same names and navigation behavior.
