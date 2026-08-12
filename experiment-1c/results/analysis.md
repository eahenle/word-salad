# Experiment 1C hardened replication and normalization matrix analysis

Rates use all scheduled trials unless explicitly labeled completed-response-only. Intervals are 95% Wilson score intervals. Interaction intervals use a deterministic paired-seed bootstrap.

## Replication versus frozen historical baseline

| condition | lanes | historical semantic | replication semantic |
| :-- | --: | --: | --: |
| signal | 1 | 10/10 | 10/10 |
| signal | 2 | 7/10 | 8/10 |
| signal | 4 | 1/10 | 1/10 |
| signal | 8 | 2/10 | 2/10 |
| all_shuffled | 1 | 0/10 | 0/10 |
| all_shuffled | 2 | 0/10 | 0/10 |
| all_shuffled | 4 | 0/10 | 0/10 |
| all_shuffled | 8 | 3/10 | 0/10 |

## Complete scheduled-denominator matrix

| variant | condition | N | trials | semantic | rate | 95% CI | nonresponses |
| :-- | :-- | --: | --: | --: | --: | :-- | --: |
| original | signal | 1 | 10 | 10 | 100% | 72%–100% | 0 |
| original | signal | 2 | 10 | 8 | 80% | 49%–94% | 0 |
| original | signal | 4 | 10 | 1 | 10% | 2%–40% | 0 |
| original | signal | 8 | 10 | 2 | 20% | 6%–51% | 0 |
| original | all_shuffled | 1 | 10 | 0 | 0% | 0%–28% | 1 |
| original | all_shuffled | 2 | 10 | 0 | 0% | 0%–28% | 0 |
| original | all_shuffled | 4 | 10 | 0 | 0% | 0%–28% | 0 |
| original | all_shuffled | 8 | 10 | 0 | 0% | 0%–28% | 0 |
| lower | signal | 1 | 10 | 10 | 100% | 72%–100% | 0 |
| lower | signal | 2 | 10 | 5 | 50% | 24%–76% | 0 |
| lower | signal | 4 | 10 | 1 | 10% | 2%–40% | 0 |
| lower | signal | 8 | 10 | 2 | 20% | 6%–51% | 0 |
| lower | all_shuffled | 1 | 10 | 1 | 10% | 2%–40% | 0 |
| lower | all_shuffled | 2 | 10 | 0 | 0% | 0%–28% | 0 |
| lower | all_shuffled | 4 | 10 | 0 | 0% | 0%–28% | 0 |
| lower | all_shuffled | 8 | 10 | 0 | 0% | 0%–28% | 0 |
| nopunct | signal | 1 | 10 | 10 | 100% | 72%–100% | 0 |
| nopunct | signal | 2 | 10 | 6 | 60% | 31%–83% | 0 |
| nopunct | signal | 4 | 10 | 4 | 40% | 17%–69% | 0 |
| nopunct | signal | 8 | 10 | 2 | 20% | 6%–51% | 0 |
| nopunct | all_shuffled | 1 | 10 | 1 | 10% | 2%–40% | 0 |
| nopunct | all_shuffled | 2 | 10 | 0 | 0% | 0%–28% | 0 |
| nopunct | all_shuffled | 4 | 10 | 0 | 0% | 0%–28% | 0 |
| nopunct | all_shuffled | 8 | 10 | 0 | 0% | 0%–28% | 0 |
| lower_nopunct | signal | 1 | 10 | 10 | 100% | 72%–100% | 0 |
| lower_nopunct | signal | 2 | 10 | 3 | 30% | 11%–60% | 0 |
| lower_nopunct | signal | 4 | 10 | 4 | 40% | 17%–69% | 0 |
| lower_nopunct | signal | 8 | 10 | 1 | 10% | 2%–40% | 0 |
| lower_nopunct | all_shuffled | 1 | 10 | 0 | 0% | 0%–28% | 0 |
| lower_nopunct | all_shuffled | 2 | 10 | 0 | 0% | 0%–28% | 0 |
| lower_nopunct | all_shuffled | 4 | 10 | 0 | 0% | 0%–28% | 0 |
| lower_nopunct | all_shuffled | 8 | 10 | 0 | 0% | 0%–28% | 0 |

## Completed-response sensitivity

Only cells containing an incomplete turn are shown. The scheduled denominator remains primary.

| variant | condition | N | scheduled semantic | completed-response semantic |
| :-- | :-- | --: | --: | --: |
| original | signal | 4 | 1/10 | 1/5 |
| original | signal | 8 | 2/10 | 2/6 |
| original | all_shuffled | 1 | 0/10 | 0/5 |
| original | all_shuffled | 2 | 0/10 | 0/5 |
| original | all_shuffled | 4 | 0/10 | 0/7 |
| original | all_shuffled | 8 | 0/10 | 0/8 |
| lower | all_shuffled | 2 | 0/10 | 0/7 |
| lower | all_shuffled | 4 | 0/10 | 0/7 |
| lower | all_shuffled | 8 | 0/10 | 0/9 |
| nopunct | signal | 4 | 4/10 | 4/8 |
| nopunct | all_shuffled | 1 | 1/10 | 1/8 |
| nopunct | all_shuffled | 2 | 0/10 | 0/7 |
| lower_nopunct | all_shuffled | 2 | 0/10 | 0/9 |
| lower_nopunct | all_shuffled | 4 | 0/10 | 0/9 |
| lower_nopunct | all_shuffled | 8 | 0/10 | 0/9 |

## Normalization interaction

Positive difference-in-differences means normalization reduced all-shuffled success more than signal success.

| variant | N | Δ signal | Δ all shuffled | interaction | bootstrap 95% CI |
| :-- | --: | --: | --: | --: | :-- |
| lower | 1 | +0% | +10% | -10% | -30%–+0% |
| lower | 2 | -30% | +0% | -30% | -60%–-10% |
| lower | 4 | +0% | +0% | +0% | -30%–+30% |
| lower | 8 | +0% | +0% | +0% | -30%–+30% |
| nopunct | 1 | +0% | +10% | -10% | -30%–+0% |
| nopunct | 2 | -20% | +0% | -20% | -60%–+30% |
| nopunct | 4 | +30% | +0% | +30% | +0%–+60% |
| nopunct | 8 | +0% | +0% | +0% | -40%–+40% |
| lower_nopunct | 1 | +0% | +0% | +0% | +0%–+0% |
| lower_nopunct | 2 | -50% | +0% | -50% | -80%–-20% |
| lower_nopunct | 4 | +30% | +0% | +30% | -10%–+70% |
| lower_nopunct | 8 | -10% | +0% | -10% | -40%–+20% |

## Computational effort

Medians exclude missing usage from incomplete turns. Timeouts remain in timeout counts and elapsed-time medians. Full N-level metrics are in `effort-summary.csv`.

| variant | condition | semantic | timeouts | tool trials | shell trials | median elapsed (s) | median input tokens | median reasoning tokens |
| :-- | :-- | --: | --: | --: | --: | --: | --: | --: |
| original | signal | 21/40 | 9 | 11 | 11 | 40.5 | 13338 | 811 |
| original | all_shuffled | 0/40 | 15 | 23 | 22 | 640.4 | 34407 | 14689 |
| lower | signal | 18/40 | 0 | 11 | 11 | 72.6 | 13790 | 2976 |
| lower | all_shuffled | 1/40 | 7 | 22 | 21 | 246.7 | 14694 | 7592 |
| nopunct | signal | 22/40 | 2 | 14 | 14 | 68.8 | 13670 | 2657 |
| nopunct | all_shuffled | 1/40 | 5 | 30 | 30 | 557.7 | 324838 | 18601 |
| lower_nopunct | signal | 18/40 | 0 | 9 | 9 | 45.2 | 13670 | 2086 |
| lower_nopunct | all_shuffled | 0/40 | 3 | 25 | 23 | 243.0 | 70063 | 8075 |

Across variants, all-shuffled trials produced 30/160 timeouts and tool use in 100/160 trials, versus 11/160 timeouts and tool use in 45/160 signal trials.
The largest cell median input context was 618438 tokens for nopunct / all_shuffled / N=1.

## Trace-derived strategies

Strategy labels describe only observable JSONL events. They do not expose private chain-of-thought.

| condition | semantic success | observable primary strategy | trials |
| :-- | :-- | :-- | --: |
| signal | yes | apparent_lexical_reconstruction | 1 |
| signal | yes | direct_one_pass_response | 57 |
| signal | yes | explicit_fixed_stride_hypothesis | 8 |
| signal | yes | explicit_testing_of_candidate_strides | 12 |
| signal | yes | shell_or_tool_assisted_reconstruction | 1 |
| signal | no | apparent_lexical_reconstruction | 3 |
| signal | no | direct_one_pass_response | 37 |
| signal | no | explicit_fixed_stride_hypothesis | 25 |
| signal | no | explicit_recognition_of_shuffled_text | 8 |
| signal | no | shell_or_tool_assisted_reconstruction | 8 |
| all_shuffled | yes | shell_or_tool_assisted_reconstruction | 2 |
| all_shuffled | no | apparent_lexical_reconstruction | 6 |
| all_shuffled | no | direct_one_pass_response | 40 |
| all_shuffled | no | explicit_fixed_stride_hypothesis | 31 |
| all_shuffled | no | explicit_recognition_of_shuffled_text | 9 |
| all_shuffled | no | explicit_testing_of_candidate_strides | 20 |
| all_shuffled | no | shell_or_tool_assisted_reconstruction | 52 |

The finer variant-by-condition strategy table is in `strategy-summary.csv`.

| variant | condition | strategy | trials |
| :-- | :-- | :-- | --: |
| original | signal | apparent_lexical_reconstruction | 1 |
| original | signal | direct_one_pass_response | 25 |
| original | signal | explicit_fixed_stride_hypothesis | 12 |
| original | signal | explicit_testing_of_candidate_strides | 1 |
| original | signal | shell_or_tool_assisted_reconstruction | 1 |
| original | all_shuffled | apparent_lexical_reconstruction | 2 |
| original | all_shuffled | direct_one_pass_response | 13 |
| original | all_shuffled | explicit_fixed_stride_hypothesis | 13 |
| original | all_shuffled | explicit_testing_of_candidate_strides | 1 |
| original | all_shuffled | shell_or_tool_assisted_reconstruction | 11 |
| lower | signal | direct_one_pass_response | 25 |
| lower | signal | explicit_fixed_stride_hypothesis | 9 |
| lower | signal | explicit_recognition_of_shuffled_text | 1 |
| lower | signal | explicit_testing_of_candidate_strides | 2 |
| lower | signal | shell_or_tool_assisted_reconstruction | 3 |
| lower | all_shuffled | direct_one_pass_response | 14 |
| lower | all_shuffled | explicit_fixed_stride_hypothesis | 6 |
| lower | all_shuffled | explicit_recognition_of_shuffled_text | 4 |
| lower | all_shuffled | explicit_testing_of_candidate_strides | 4 |
| lower | all_shuffled | shell_or_tool_assisted_reconstruction | 12 |
| nopunct | signal | direct_one_pass_response | 21 |
| nopunct | signal | explicit_fixed_stride_hypothesis | 10 |
| nopunct | signal | explicit_recognition_of_shuffled_text | 2 |
| nopunct | signal | explicit_testing_of_candidate_strides | 5 |
| nopunct | signal | shell_or_tool_assisted_reconstruction | 2 |
| nopunct | all_shuffled | apparent_lexical_reconstruction | 3 |
| nopunct | all_shuffled | direct_one_pass_response | 3 |
| nopunct | all_shuffled | explicit_fixed_stride_hypothesis | 7 |
| nopunct | all_shuffled | explicit_recognition_of_shuffled_text | 3 |
| nopunct | all_shuffled | explicit_testing_of_candidate_strides | 10 |
| nopunct | all_shuffled | shell_or_tool_assisted_reconstruction | 14 |
| lower_nopunct | signal | apparent_lexical_reconstruction | 3 |
| lower_nopunct | signal | direct_one_pass_response | 23 |
| lower_nopunct | signal | explicit_fixed_stride_hypothesis | 2 |
| lower_nopunct | signal | explicit_recognition_of_shuffled_text | 5 |
| lower_nopunct | signal | explicit_testing_of_candidate_strides | 4 |
| lower_nopunct | signal | shell_or_tool_assisted_reconstruction | 3 |
| lower_nopunct | all_shuffled | apparent_lexical_reconstruction | 1 |
| lower_nopunct | all_shuffled | direct_one_pass_response | 10 |
| lower_nopunct | all_shuffled | explicit_fixed_stride_hypothesis | 5 |
| lower_nopunct | all_shuffled | explicit_recognition_of_shuffled_text | 2 |
| lower_nopunct | all_shuffled | explicit_testing_of_candidate_strides | 5 |
| lower_nopunct | all_shuffled | shell_or_tool_assisted_reconstruction | 17 |

## Observable unusual behavior counts

- Timeout/nonresponse runner events: 41
- Final responses explicitly mentioning shuffle/encoding: 93
- Responses with malformed object substitutions: 22
- Correct signal trials with a direct/no-tool/no-explicit-reconstruction primary trace label: 57/79
- Correct signal trials with any observable tool call: 20/79
- Correct all-shuffled trials with any observable tool call: 2/2
- Some timed-out traces ended on progress messages after recognizing the task or scrambling; those are not final task successes.
- Several failures substituted material/object pairs such as `brass coin` or `silver key`, consistent with lexical recombination rather than reliable relational recovery.

## Conclusion and next step

The preregistered directional hypothesis was not supported. Normalization did eliminate or reduce the original N=8 all-shuffled successes, but it generally damaged intact-signal recovery as much or more; the paired interaction estimates were zero or negative in most cells. The result therefore does not isolate punctuation/capitalization as a cue used disproportionately for unordered reconstruction.

The fully instrumented replication did reproduce robust blind task recovery and substantial run-to-run variability. Observable traces separate many cheap direct responses from expensive tool-assisted reconstruction, but a direct final response cannot establish implicit decoding because the payload itself suppresses explanation.

Proceed to the preregistered equal-multiset A/B Experiment 2 without changing its central design. Its answer-identity endpoint is more discriminating than another success-rate comparison. Retain full traces, the explanation-permitted arm, and the tool-less regime so that ordered-channel sensitivity can be separated from explicit agentic reconstruction.

## Interpretation boundary

Correct all-shuffled answers are not periodic-lane recovery. Final-answer silence about encoding is not evidence that encoding was not consciously discovered, especially because the payload suppresses explanation. Statistical summaries describe repeatability for this model/runtime rather than classical population inference.
