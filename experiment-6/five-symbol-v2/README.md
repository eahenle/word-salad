# Experiment 6 five-symbol task v2

Task v1 failed clean validation at 0/40 despite complete, error-free responses.
Its use of “rotate left” was removed. Version 2 uses only two explicit,
overlapping positional swaps, states that position one is leftmost, and requires
the final left-to-right sequence.

The two exact whitespace-word bags are identical. Every candidate symbol occurs
once. Deterministic answers are:

```text
A (swap 1↔4, then 1↔2) -> Birch Dune Cobalt Aster Ember
B (swap 1↔2, then 1↔4) -> Dune Aster Cobalt Birch Ember
```

The v1 failure is frozen at tag
`experiment-6-five-symbol-v1-clean-failed`; no v1 scrambled or buried-signal
prompt is eligible to run.

## Clean gate

Run 20 fresh A and 20 fresh B subjects with `gpt-5.6-sol`, reasoning `medium`,
no tools, and the exact audited Docker image. Each identity must reach at least
18/20 normalized-exact outputs. Failure freezes v2 and ends this task version.

No scrambled or buried-signal v2 prompt is generated before the clean gate.
