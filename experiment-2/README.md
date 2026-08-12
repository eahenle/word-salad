# Experiment 2: paired equal-multiset ordered payloads

This experiment tests whether changing only the ordering of one coherent sparse
stream changes GPT-5.6-Sol-xhigh's answer. Payloads A and B use the same six
operation sentences and exactly the same whitespace-delimited word multiset;
only operations 5 and 6 exchange positions. A deterministic state simulator
validates that their final answers differ.

The protocol is staged after the frozen, hardened Experiment 1C dataset. Its
primary endpoint is answer identity: A-like versus B-like output, not generic
success. Planned signal conditions use N=2 and N=4 first, with identical phase,
distractor index permutations, prompt length, and aggregate bag of words for
each paired seed. Clean A/B validate task execution. All-shuffled prompts
measure residual answer bias.

Two output arms are planned: constrained final-answer only and explanation
permitted. The latter requests a brief account without mentioning ciphers,
interleaving, strides, or hidden messages. Codex-agent trials retain the pinned
hardened container and full raw traces. A tool-less GPT-5.6-Sol-xhigh regime
will run only if that exact direct invocation is available; no model
substitution is permitted.

Generate and validate payloads with:

```bash
python3 -B experiment-2/simulate.py
```

Answer keys exist only in coordinator-side simulation output/results and must
never be mounted or sent into subject containers.

## Pilot freeze

The seed-1 pilot completed clean A/B, N=2 signal A/B, and N=2 all-shuffled
trials in both arms. Its artifact audit passed and no host or experiment-context
leakage was observed. See `results/pilot-report.md`. The protocol was frozen
without modification before launching the remaining 20-seed N=2/N=4 slate.
