# Balanced-density ladder: frozen result

## Behavioral outcomes

| stage | density | expected | pairs | scrambled targets | counterpart errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| d075 | 0.0751 | 0/6 | 0/3 | 0/3 | 0 |
| d125 | 0.1250 | 0/6 | 0/3 | 0/3 | 0 |
| d250 | 0.2500 | 1/6 | 0/3 | 0/3 | 0 |
| d500 | 0.5000 | 0/6 | 0/3 | 1/3 | 1 |

No density met the preregistered recovery gate. The single exact hidden-B answer at 25% was not accompanied by its paired hidden-A answer. At 50%, one scrambled control produced target A and one hidden-B trial produced the counterpart target A; the control gate therefore failed and the ladder stopped.

This dataset does not establish a density boundary. It does show isolated and partial task reconstruction at 25% and 50%, but not reliable answer-identity tracking attributable to hidden word order.

## Computational effort

| stage | median elapsed, all trials (s) | median reasoning tokens, all trials |
| --- | ---: | ---: |
| d075 | 75.938 | 2366.0 |
| d125 | 140.985 | 4672.0 |
| d250 | 191.252 | 6266.0 |
| d500 | 19.075 | 634.0 |

Median effort rose through 25% and then fell sharply at 50%. This is descriptive: only nine trials were run per stage, and condition-specific medians are preserved in `effort-summary.csv`.

## Observable behavior

The post-hoc trace audit covers all 36 frozen trials and uses only emitted agent messages. It does not claim access to private reasoning. Explicit structural language appeared in 5/9, 7/9, 5/9, and 4/9 trials from 7.5% through 50%. At 50%, seven responses mentioned all three symbols and two mentioned both operations. Two signal responses visibly recovered substantial task structure but admitted capitalized noise words into the initial state. The exact 25% success explicitly described tracing an interleaved sequence; its paired A trial instead reconstructed foreground material.

## Execution audit

Two original d250 scrambled attempts failed before any model response because the credential refresh token had expired and was reported as reused. The attempts and the pre-rerun cohort freeze are preserved under `stages/d250/invalidated-attempts/`. Only those two trials were rerun, both completed normally, and the invalidated attempts are excluded from behavioral and effort summaries. No subject trial used a direct API.

## Limitations and next design

The replacement task was mechanically simulated but was not validated on clean N=1 model trials before the density ladder. The malformed and counterpart outputs at 50% therefore cannot cleanly separate carrier acquisition from task interpretation/execution.

Although scoring a three-symbol full state repaired unequal answer-symbol frequency, the two preregistered targets still occupy 2 of the 6 possible permutations. A model that merely emits a permutation therefore has a 1/3 target-space hit rate, consistent with why the strict scrambled-control gate was necessary.

The next experiment should first clean-validate an equal-bag, five-symbol task, then use full five-symbol permutations (two targets among 120 possibilities) in small matched A/B/scrambled cohorts at the informative 25% and 50% densities. No further trial from this ladder should be interpreted as a population estimate.

## Context-audit relation

The separate C1 audit recovered 0/5 high-entropy canaries stored only in prior Codex cloud history, while 5/5 nonexistent controls returned `UNKNOWN`. The historical trace audit found experiment-aware language overwhelmingly in visibly multiplexed or decohered stimuli, not ordinary coherent 4C text. These results weaken, but do not prove the universal absence of, nonlocal context leakage.
