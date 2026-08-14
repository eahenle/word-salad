# Experiment 4C development analysis

## Outcome

The preregistered development gate did not pass; no held-out or optimized follow-up was run.

The result is a twelve-trial development gate, not a population estimate.

## Answer identity

| Topic | Hidden A (Rowan) | Hidden B (Mira) | Scrambled | Cover only | Complete A/B pair |
| --- | --- | --- | --- | --- | ---: |
| ceramics | no target answer | no target answer | no target answer | no target answer | no |
| garden | no target answer | no target answer | no target answer | no target answer | no |
| harbor | both target names | no target answer | both target names | no target answer | no |

## Gate metrics

- Expected hidden answers: 0/6.
- Complete A/B pairs: 0/3 (required: at least 2).
- Control target-answer selections: 0/6 (required: 0).
- Counterpart-answer errors: 0.

## Observable execution

- Observable non-message/tool items: 12 trials: ceramics_cover_only, ceramics_hidden_a, ceramics_hidden_b, ceramics_scrambled, garden_cover_only, garden_hidden_a, garden_hidden_b, garden_scrambled, harbor_cover_only, harbor_hidden_a, harbor_hidden_b, harbor_scrambled.
- Explicit hidden/encoded-structure mentions: 0 trials.
- Timeouts: 0.
- Median elapsed time: 21.531 seconds.
- Median reasoning-output tokens: 504.5.

## Interpretation boundary

These covers do not establish dual-channel recovery. The negative gate cannot distinguish coherent-foreground suppression, low signal density, grammar-constrained carrier difficulty, and neutral-framing effects. The protocol forbids rewriting these covers to optimize toward success.

The local Docker audit found no observable baked-in project context, but did not rule out every possible upstream or account-level context.

## Data integrity

Hidden A, Hidden B, and scrambled documents have exactly equal complete whitespace-word bags within each topic. Every consecutive selected signal position is separated far enough that no visible 2-6 word window contains two selected signal words. Subjects received no tool schema or project mount.
