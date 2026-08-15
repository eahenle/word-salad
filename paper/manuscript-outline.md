# Manuscript outline

## Abstract

State the equal-word-bag behavioral result, tool-less replication, carrier
generalization, model-specific boundary, and limits. Avoid mechanistic claims.

## Introduction

- Lexical content versus relational word order.
- Robustness to corrupted and competing language.
- Source separation as a behavioral analogy, not a claimed mechanism.
- Question: can an LLM use a coherent ordered subsequence under matched lexical
  interference?

## Methods

- Payload state-transition tasks and deterministic simulators.
- Equal-multiset A/B construction.
- Fixed, balanced-jitter, and uniform-random carriers.
- Isolation, fresh subjects, traces, freezing, and retry policy.
- Answer-identity scoring and paired endpoints.

## Results

1. Initial recovery and hardened normalization replication.
2. Equal-word-bag A/B discrimination eliminates bag-of-words inference.
3. Tool-less N=2 replication eliminates shell/filesystem necessity.
4. Balanced jitter eliminates fixed-period necessity.
5. Uniform random placement eliminates a designed carrier schedule.
6. Model-family and observable-effort differences.
7. Boundary studies: coherent foreground and low-density nulls.
8. Preregistered five-symbol instrument failure and experimental stop.

## Discussion

- Established behavioral sensitivity to sparse linguistic order.
- Alternative mechanisms left open.
- Density, foreground, proprietary-model, and runtime limitations.
- Security/robustness relevance as future work, not demonstrated exploitation.

## Reproducibility and data availability

- Frozen tags and hashes.
- Complete active traces and invalidated-attempt archives.
- Machine-generated tables and figures.

## Drafting decision

No additional experiment is required to support the central claim. Begin a
manuscript from the frozen Experiments 1C–4A chain. Treat external replication,
human readability baselines, and testing open-weight models as valuable future
work rather than conditions for drafting this model-specific behavioral report.
