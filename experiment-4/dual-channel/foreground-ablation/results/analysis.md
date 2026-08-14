# Experiment 4C.1 foreground-coherence ablation

## Direct matched comparison

| Topic | 4C coherent A | 4C coherent B | 4C.1 decohered A | 4C.1 decohered B | Decohered scrambled |
| --- | --- | --- | --- | --- | --- |
| harbor | both target names | no target answer | neither target | neither target | neither target |
| ceramics | no target answer | no target answer | neither target | both target names | neither target |
| garden | no target answer | no target answer | both target names | neither target | neither target |

## Aggregate

- 4C coherent expected individuals: 0/6.
- 4C coherent complete pairs: 0/3.
- 4C.1 decohered expected individuals: 0/6.
- 4C.1 decohered complete pairs: 0/3.
- Decohered scrambled target selections: 0/3.
- Counterpart errors: 0.

## Preregistered interpretation

Destroying foreground coherence did not restore any expected hidden answer. Foreground coherence is therefore not sufficient to explain the 4C failure; low signal density becomes the leading next variable.

## Observable behavior

- Explicit structural-analysis language: 0/9.
- Explicit hidden/encoded-content mentions: 0/9.
- Clarification requests: 0/9.
- Timeouts: 0/9.
- Median elapsed time: 47.751 seconds.
- Median reasoning-output tokens: 1285.0.

These three topics form a controlled mechanistic ablation, not a population sample. The experiment does not identify a private reasoning process or transformer mechanism.

## Integrity

Every decohered document retains the frozen 4C signal words at the exact same 19 indices, the exact document length, and the exact complete whitespace-word multiset. Only nonsignal assignment changed. The model, reasoning effort, framing, clean image, no-tool configuration, and ten-minute timeout were unchanged.
