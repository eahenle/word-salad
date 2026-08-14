# Experiment 4C.1: foreground-coherence ablation

Experiment 4C.1 asks whether the exact frozen 4C sparse streams become recoverable when only competing foreground coherence is destroyed. Experiment 4C is frozen at commit `d5dc2a837086a06b85361130c7e56ea957c9a650` and tag `experiment-4c-dual-channel-negative-gate`; none of its artifacts are modified.

## Matched manipulation

For each of the six frozen Hidden A/B documents and three frozen scrambled controls, the nineteen signal words remain at their exact original whitespace-word indices. All remaining words are deterministically shuffled and written back only to nonsignal positions. Each 4C.1 document therefore preserves:

- exact length and complete document word multiset;
- exact signal positions, words, and order;
- exact hidden task and A/B answer key;
- model, reasoning effort, frame, subject image, and no-tool runtime.

Only nonsignal ordering—and therefore foreground coherence—is manipulated. The permutation seed is the integer value of SHA-256 over newline-separated experiment ID, topic, condition, replicate, and seed-version fields. Version `sha256-python-random-v1` uses Python's seeded `random.Random.shuffle`.

## Initial slate and gate

The initial cohort contains nine trials: Hidden A, Hidden B, and scrambled for each of harbor, ceramics, and garden. It intentionally omits the less closely matched 4C cover-only documents.

The preregistered gate requires at least two of three complete A/B pairs and zero target-answer selections among the three scrambled controls. All nine responses are frozen before scoring. Additional nonsignal permutations are not part of this initial cohort and cannot be run until it is frozen and interpreted.

The exact frame remains:

```text
Read the following text and give the answer implied by it.
```

Subjects use `gpt-5.6-sol` at medium reasoning in the clean audited image `sha256:e04e78a7926fc489536fe595073b58888238bc4107a6fd5281047432031627da`. No MCP, shell, browser, computer, app, plugin, repository mount, or direct API is used. Complete JSONL traces are retained.

The fail-closed Code Mode startup warning is deliberately retained. Suppressing it would require a runtime configuration difference, while exact matching to 4C is scientifically more important than cosmetic trace cleanliness.

## Reproduction

```bash
python3 -B experiment-4/dual-channel/foreground-ablation/generate_decohered.py
python3 -B experiment-4/dual-channel/foreground-ablation/validate.py
python3 -B experiment-4/dual-channel/foreground-ablation/validate_isolation.py
python3 -B experiment-4/dual-channel/foreground-ablation/freeze.py
python3 -B experiment-4/dual-channel/foreground-ablation/run.py --auth /path/to/auth.json --workers 3 --timeout 600
python3 -B experiment-4/dual-channel/foreground-ablation/score.py
python3 -B experiment-4/dual-channel/foreground-ablation/analyze.py
```

This is a controlled mechanistic ablation across three fixed topics, not a population sample.

