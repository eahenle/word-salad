# Experiment 4A uniform-random carrier analysis

## Main result

Recovery survived uniform-random placement in both preregistered cells. Sol-medium produced 30/40 expected individual answers and 13/20 complete A/B pairs. Terra-xhigh produced 16/40 and 5/20. Aggregate uniform performance was 46/80 individual answers and 18/40 pairs.

The same two configurations' frozen balanced-jitter aggregate was 49/80 individual answers and 18/40 pairs. Their fixed aggregate was 38/80 and 12/40. Uniform placement therefore preserved paired recovery exactly at the two-cell aggregate level relative to balanced jitter; it did not collapse when the designed 1/3 interval structure was removed.

## Carrier comparison

| model | carrier | individual expected | complete A/B pairs |
| --- | --- | ---: | ---: |
| Sol-medium | fixed | 25/40 | 10/20 |
| Sol-medium | jitter | 30/40 | 12/20 |
| Sol-medium | uniform | 30/40 | 13/20 |
| Terra-xhigh | fixed | 13/40 | 2/20 |
| Terra-xhigh | jitter | 19/40 | 6/20 |
| Terra-xhigh | uniform | 16/40 | 5/20 |

Against balanced jitter, the matched individual comparison had 18 jitter-only and 15 uniform-only successes (exact McNemar p=0.7283); paired discordances were 9 and 9 (p=1). These are repeatability summaries, not population inference over models.

## Controls and execution

The 10 all-shuffled controls produced 0 target A/B answers. All 90 scheduled subjects completed without timeout or runner error. No control expansion was triggered.

| model | condition | trials | success/targets | tool users | median seconds | median reasoning tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Sol-medium | signal | 40 | 30 | 0 | 17.5 | 358 |
| Sol-medium | all_shuffled | 5 | 0 | 1 | 52.5 | 1472 |
| Terra-xhigh | signal | 40 | 16 | 0 | 24.4 | 1034 |
| Terra-xhigh | all_shuffled | 5 | 0 | 1 | 43.7 | 2070 |

## Observable strategy

Among 46 successful signal trials, observable strategies were: `direct_one_pass_tool_free` 46. The labels use emitted events only and do not claim access to private chain of thought.

## Exploratory mask statistics

Per-seed run lengths, adjacent-signal counts, gap means, and gap variances are preserved in `mask-outcomes.csv`. With only 20 masks and two model cells, these post hoc values are descriptive and were not used to reject masks or tune prompts.

## Interpretation

These data support the claim that ordered linguistic recovery does not require a fixed carrier or the balanced-jitter generator's simple deterministic placement rule. The model can recover a coherent ordered subsequence under a uniformly sampled 50%-density carrier with lexically matched interference.

This does not establish arbitrary dilution levels, adversarially chosen masks, or a specific transformer mechanism. It does justify proceeding to the separately frozen natural-prose harmless-canary PoC. Cover construction must use development/held-out separation and must not optimize held-out passages against target responses.
