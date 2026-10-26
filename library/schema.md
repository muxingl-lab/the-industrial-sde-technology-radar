# Pattern Registry Schema

[Problem library](README.md) · [Pattern comparisons](comparisons/README.md) · [Contributing](../CONTRIBUTING.md)

The radar models overlap as a many-to-many graph, not as a collection of pairwise articles.

```text
service-question  ── belongs to ──>  pattern  <── belongs to ──  service-question
      │                                  │
      └── three learning levels          └── one N-way comparison chapter
```

`patterns.json` is the canonical registry. The Markdown library and comparison index are reader-facing views of that graph.

## Stable identities

A member reference has the form `service:qN`, for example `redis:q1`. It identifies one question across all three learning levels. Titles and Markdown anchors may improve over time without changing this identity.

A pattern has a stable lowercase ID such as `bounded-work`. Its comparison chapter is organized around the shared failure and invariant, not around a fixed pair of products.

## Pattern record

| Field | Contract |
|---|---|
| `id` | Unique stable pattern identity; lowercase letters, digits, and hyphens |
| `title` | Human-readable pattern name |
| `summary` | One sentence describing the transferable mechanism |
| `comparison` | Repository-relative chapter under `library/comparisons/` |
| `dimensions` | The questions used to compare every member on equal terms |
| `members` | Unique `service:qN` references; two or more for a cross-system comparison |

Membership is deliberately non-exclusive. For example, `sglang:q10` participates in both ownership and backpressure because a staged pipeline must solve both problems. Do not force a question into one taxonomy bucket.

## Scaling rule

Adding a service with `P` questions requires `P` library rows and only the relevant pattern memberships. It does not require a page against every existing service. If five services implement bounded work, all five join `bounded-work`; the one comparison chapter expands along its declared dimensions.

Create a new pattern only when the triggering failure, invariant, or engineering decision is materially different. A comparison can grow from two to many members without changing its ID or URL.
