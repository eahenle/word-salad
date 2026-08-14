# Experiment 3 screening analysis

## Main result

Across 12 exact model/reasoning configurations, fixed carriers produced 69/240 expected individual answers and 17/120 complete A/B pairs. Balanced jitter produced 95/240 individual answers and 31/120 pairs. The paired jitter penalty was therefore -11.7% (negative means jitter performed better).

The within-cell matched comparison had 8 fixed-only versus 22 jitter-only paired successes (two-sided exact McNemar p=0.01612). At the individual-prompt level the corresponding counts were 24 and 50 (p=0.003372). These repeatability summaries are not population inference over models.

A strict period-2 carrier is not required. The balanced jitter manipulation did not merely preserve recovery; it improved aggregate recovery. This does not show that arbitrary sparse placement is equally recoverable: the 1/3 interval mask creates runs of adjacent signal words, which may supply stronger local coherence than alternation. Uniform random placement is now the most discriminating structural follow-up.

## Model and effort matrix

| model | effort | fixed individual | fixed pairs | jitter individual | jitter pairs | paired jitter penalty | signal tool use | timeouts |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Sol | medium | 11/20 | 4/10 | 16/20 | 6/10 | -20% | 0% | 0 |
| Sol | high | 8/20 | 3/10 | 16/20 | 6/10 | -30% | 0% | 0 |
| Sol | xhigh | 13/20 | 5/10 | 17/20 | 7/10 | -20% | 2% | 1 |
| Terra | medium | 3/20 | 0/10 | 9/20 | 3/10 | -30% | 0% | 0 |
| Terra | high | 7/20 | 1/10 | 5/20 | 1/10 | 0% | 2% | 0 |
| Terra | xhigh | 6/20 | 0/10 | 10/20 | 3/10 | -30% | 0% | 0 |
| Luna | medium | 5/20 | 1/10 | 6/20 | 0/10 | 10% | 0% | 1 |
| Luna | high | 8/20 | 1/10 | 5/20 | 2/10 | -10% | 0% | 2 |
| Luna | xhigh | 8/20 | 2/10 | 10/20 | 3/10 | -10% | 2% | 1 |
| Spark | medium | 0/20 | 0/10 | 0/20 | 0/10 | 0% | 22% | 0 |
| Spark | high | 0/20 | 0/10 | 0/20 | 0/10 | 0% | 30% | 0 |
| Spark | xhigh | 0/20 | 0/10 | 1/20 | 0/10 | 0% | 38% | 0 |

Reasoning effort was not monotonic. Sol remained strongest at every effort, Terra and Luna were intermediate, and Spark showed a sharp lower boundary: one expected jitter answer at xhigh, but no complete A/B pair at any Spark effort. Higher effort sometimes increased recovery and sometimes reduced it.

## Controls and answer bias

The 36 all-shuffled controls produced 0 target A/B answers. 4 controls reached 900 seconds. The absence of target answers across all model/effort cells argues against a generic bag-of-words target bias in this cohort.

## Computational effort

| model | effort | carrier | trials | success | timeout | tool users | median seconds | median reasoning tokens |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Spark | high | all-shuffled | 3 | 0 | 0 | 0 | 8.3 | 3109 |
| Spark | high | fixed | 20 | 0 | 0 | 2 | 10.9 | 4897 |
| Spark | high | jitter | 20 | 0 | 0 | 10 | 20.2 | 12621 |
| Spark | medium | all-shuffled | 3 | 0 | 0 | 0 | 6.8 | 1685 |
| Spark | medium | fixed | 20 | 0 | 0 | 3 | 9.4 | 3331 |
| Spark | medium | jitter | 20 | 0 | 0 | 6 | 12.1 | 6048 |
| Spark | xhigh | all-shuffled | 3 | 0 | 0 | 0 | 10.4 | 1928 |
| Spark | xhigh | fixed | 20 | 0 | 0 | 3 | 12.3 | 6342 |
| Spark | xhigh | jitter | 20 | 1 | 0 | 12 | 23.7 | 14118 |
| Luna | high | all-shuffled | 3 | 0 | 1 | 1 | 335.7 | 12626 |
| Luna | high | fixed | 20 | 8 | 0 | 0 | 38.7 | 1838 |
| Luna | high | jitter | 20 | 5 | 1 | 0 | 33.3 | 1432 |
| Luna | medium | all-shuffled | 3 | 0 | 1 | 0 | 76.4 | 3352 |
| Luna | medium | fixed | 20 | 5 | 0 | 0 | 31.0 | 1387 |
| Luna | medium | jitter | 20 | 6 | 0 | 0 | 24.8 | 1024 |
| Luna | xhigh | all-shuffled | 3 | 0 | 1 | 2 | 352.1 | 18224 |
| Luna | xhigh | fixed | 20 | 8 | 0 | 1 | 65.0 | 3308 |
| Luna | xhigh | jitter | 20 | 10 | 0 | 0 | 43.1 | 2066 |
| Sol | high | all-shuffled | 3 | 0 | 0 | 1 | 451.4 | 14381 |
| Sol | high | fixed | 20 | 8 | 0 | 0 | 23.3 | 710 |
| Sol | high | jitter | 20 | 16 | 0 | 0 | 21.7 | 723 |
| Sol | medium | all-shuffled | 3 | 0 | 0 | 2 | 151.2 | 4789 |
| Sol | medium | fixed | 20 | 11 | 0 | 0 | 24.0 | 796 |
| Sol | medium | jitter | 20 | 16 | 0 | 0 | 17.8 | 472 |
| Sol | xhigh | all-shuffled | 3 | 0 | 1 | 3 | 817.3 | 20051 |
| Sol | xhigh | fixed | 20 | 13 | 0 | 1 | 26.4 | 1075 |
| Sol | xhigh | jitter | 20 | 17 | 0 | 0 | 25.4 | 1014 |
| Terra | high | all-shuffled | 3 | 0 | 0 | 0 | 38.7 | 1798 |
| Terra | high | fixed | 20 | 7 | 0 | 1 | 27.5 | 1010 |
| Terra | high | jitter | 20 | 5 | 0 | 0 | 18.8 | 603 |
| Terra | medium | all-shuffled | 3 | 0 | 0 | 0 | 24.3 | 978 |
| Terra | medium | fixed | 20 | 3 | 0 | 0 | 22.3 | 890 |
| Terra | medium | jitter | 20 | 9 | 0 | 0 | 16.0 | 486 |
| Terra | xhigh | all-shuffled | 3 | 0 | 0 | 0 | 71.2 | 3624 |
| Terra | xhigh | fixed | 20 | 6 | 0 | 0 | 39.5 | 1737 |
| Terra | xhigh | jitter | 20 | 10 | 0 | 0 | 32.5 | 1466 |

Timeouts were retained as scheduled-trial outcomes. There were no broken pipes, connection resets, capacity failures, or other retry-eligible infrastructure errors. The only signal timeout was Luna-high jitter q0046; the remaining timeouts were all-shuffled controls.

## Observable trace strategies

Among 164 successful signal trials, 160 were observable one-pass tool-free responses and 4 used a tool. Concrete fixed-stride evidence appeared in 1 successful traces; concrete jitter-pattern language appeared in 0. Final-answer silence is not evidence that no pattern was noticed, and emitted traces do not expose private chain of thought.

| strategy | successful signals | failed signals | controls |
| --- | ---: | ---: | ---: |
| direct_one_pass_tool_free | 160 | 199 | 4 |
| explicit_fixed_stride_recognition | 0 | 0 | 1 |
| explicit_stride_testing | 1 | 0 | 4 |
| generic_corruption_detection | 0 | 69 | 16 |
| indeterminate | 0 | 1 | 3 |
| lexical_reconstruction_without_stride | 2 | 14 | 6 |
| repeated_reconstruction | 1 | 19 | 2 |
| shell_or_tool_assisted_decoder | 0 | 14 | 0 |

The classifications require concrete observable evidence. In particular, `explicit_stride_testing` requires actual candidate-stride language or code, and `explicit_fixed_stride_recognition` requires parity/every-other/residue extraction evidence. Generic complaints about scrambled text are not promoted to stride discovery.

## Scoring and integrity audit

Semantic scoring accepts both the requested object-to-color form and an unambiguous inverse box-to-contents form. A post-freeze audit added this surface normalization uniformly. If an object appears in multiple reported boxes, it is not assigned by the inverse parser. The scorer tests include both visible-label and physical-box-to-visible-label renderings.

All 473 fresh screening traces, 23 fresh anchor traces, and 20 reused fixed-reference traces matched their frozen hashes. Prior Experiment 1C/2 worktrees remained unchanged. The isolation audit passed; no credentials were stored in the experiment tree. Same-host Docker is an audited practical boundary, not cryptographic multi-host isolation.

## Boundary confirmation

The preregistered 120-trial boundary confirmation is complete and reported separately in `confirmation-analysis.md`. In its fresh half, fixed and jitter produced 8/30 and 9/30 complete pairs. Cumulatively, Sol-medium reached 10/20 fixed versus 12/20 jitter pairs, Terra-xhigh 2/20 versus 6/20, and Spark-xhigh 0/20 versus 0/20. The confirmation preserves the no-collapse conclusion while showing that the screening-wide jitter advantage was not equally large in fresh seeds.

## Interpretation

The data support general ordered-stream recovery beyond a fixed positional clock and a strong model-family capability gradient. They do not identify a specific transformer mechanism. The jitter advantage could reflect burst-local coherence, and effort effects are nonmonotonic. The decisive next carrier test is uniform random signal placement with the same word bags and density.
