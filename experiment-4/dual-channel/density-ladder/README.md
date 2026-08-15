# Experiment 4C.2: incoherent-interference density ladder

Experiment 4C.2 follows the clean 7.4% nulls in Experiments 4C and 4C.1. It asks at what signal density the unchanged nineteen-word A/B task becomes recoverable in incoherent lexical interference.

## Frozen staged design

The initial ladder is sequential rather than Cartesian:

| Stage | Signal | Noise | Total | Density |
| --- | ---: | ---: | ---: | ---: |
| `d125` | 19 | 133 | 152 | 12.5% |
| `d250` | 19 | 57 | 76 | 25% |

A 50% generator configuration exists for future reproducibility but is not authorized in this initial ladder.

For each topic, A, B, and scrambled use the same uniformly sampled carrier mask and the same nonsignal words in the same positions. Their complete word bags are therefore identical; only the order of the nineteen signal words differs. Nonsignal samples are nested: the 57 noise tokens at 25% are a subset of the 133 at 12.5%. Masks are sampled without conditioning on run structure.

The payload, answer keys (`A -> Rowan`, `B -> Mira`), neutral frame, `gpt-5.6-sol` medium subject, clean audited image, no-tool runtime, and ten-minute timeout are unchanged.

## Decision rule

Each stage contains three topics by A/B/scrambled, or nine trials. The gate requires at least two complete A/B pairs and zero scrambled target selections.

- A clean 12.5% complete null authorizes 25%.
- A clean 12.5% gate pass stops for confirmation at 12.5%.
- Partial recovery stops for independent replication rather than advancing.
- Any target selection in scrambled controls stops for control audit.
- The 25% stage always stops this initial ladder after scoring.

All responses in a stage freeze before scoring. Traces are inspected only after all authorized stages finish.

## Reproduction

```bash
python3 -B experiment-4/dual-channel/density-ladder/generate.py d125
python3 -B experiment-4/dual-channel/density-ladder/validate.py d125
python3 -B experiment-4/dual-channel/density-ladder/validate_isolation.py
python3 -B experiment-4/dual-channel/density-ladder/freeze_protocol.py
python3 -B experiment-4/dual-channel/density-ladder/freeze_stage.py d125
python3 -B experiment-4/dual-channel/density-ladder/run_stage.py d125 --auth /path/to/auth.json --workers 3 --timeout 600
python3 -B experiment-4/dual-channel/density-ladder/score_stage.py d125
```

Run the equivalent `d250` commands only when the frozen `d125` decision authorizes them. No direct API calls are used. Density necessarily covaries with total prompt length because the signal is fixed at nineteen words; this is an explicit limitation.

