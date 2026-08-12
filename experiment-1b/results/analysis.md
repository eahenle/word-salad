# Experiment 1A-R and 1B analysis

> **INVALIDATED DATASET — FORENSIC USE ONLY.** Post-slate trace review found behavior-dependent host filesystem leakage. See `invalidation-report.md` and `leakage-trace-audit-summary.json`. These results must not be used for confirmatory inference or pooled with a hardened rerun.

Rates use all scheduled trials unless explicitly labeled completed-response-only. Intervals are 95% Wilson score intervals. Interaction intervals use a deterministic paired-seed bootstrap.

## Replication versus frozen historical baseline

| condition | lanes | historical semantic | replication semantic |
| :-- | --: | --: | --: |
| signal | 1 | 10/10 | 10/10 |
| signal | 2 | 7/10 | 10/10 |
| signal | 4 | 1/10 | 4/10 |
| signal | 8 | 2/10 | 4/10 |
| all_shuffled | 1 | 0/10 | 0/10 |
| all_shuffled | 2 | 0/10 | 0/10 |
| all_shuffled | 4 | 0/10 | 0/10 |
| all_shuffled | 8 | 3/10 | 3/10 |

## Complete scheduled-denominator matrix

| variant | condition | N | trials | semantic | rate | 95% CI | nonresponses |
| :-- | :-- | --: | --: | --: | --: | :-- | --: |
| original | signal | 1 | 10 | 10 | 100% | 72%–100% | 0 |
| original | signal | 2 | 10 | 10 | 100% | 72%–100% | 0 |
| original | signal | 4 | 10 | 4 | 40% | 17%–69% | 0 |
| original | signal | 8 | 10 | 4 | 40% | 17%–69% | 0 |
| original | all_shuffled | 1 | 10 | 0 | 0% | 0%–28% | 0 |
| original | all_shuffled | 2 | 10 | 0 | 0% | 0%–28% | 0 |
| original | all_shuffled | 4 | 10 | 0 | 0% | 0%–28% | 0 |
| original | all_shuffled | 8 | 10 | 3 | 30% | 11%–60% | 0 |
| lower | signal | 1 | 10 | 10 | 100% | 72%–100% | 0 |
| lower | signal | 2 | 10 | 5 | 50% | 24%–76% | 0 |
| lower | signal | 4 | 10 | 1 | 10% | 2%–40% | 0 |
| lower | signal | 8 | 10 | 1 | 10% | 2%–40% | 0 |
| lower | all_shuffled | 1 | 10 | 0 | 0% | 0%–28% | 0 |
| lower | all_shuffled | 2 | 10 | 0 | 0% | 0%–28% | 0 |
| lower | all_shuffled | 4 | 10 | 1 | 10% | 2%–40% | 0 |
| lower | all_shuffled | 8 | 10 | 0 | 0% | 0%–28% | 0 |
| nopunct | signal | 1 | 10 | 10 | 100% | 72%–100% | 0 |
| nopunct | signal | 2 | 10 | 5 | 50% | 24%–76% | 0 |
| nopunct | signal | 4 | 10 | 5 | 50% | 24%–76% | 0 |
| nopunct | signal | 8 | 10 | 2 | 20% | 6%–51% | 0 |
| nopunct | all_shuffled | 1 | 10 | 0 | 0% | 0%–28% | 0 |
| nopunct | all_shuffled | 2 | 10 | 0 | 0% | 0%–28% | 0 |
| nopunct | all_shuffled | 4 | 10 | 0 | 0% | 0%–28% | 0 |
| nopunct | all_shuffled | 8 | 10 | 1 | 10% | 2%–40% | 0 |
| lower_nopunct | signal | 1 | 10 | 10 | 100% | 72%–100% | 0 |
| lower_nopunct | signal | 2 | 10 | 4 | 40% | 17%–69% | 0 |
| lower_nopunct | signal | 4 | 10 | 2 | 20% | 6%–51% | 0 |
| lower_nopunct | signal | 8 | 10 | 1 | 10% | 2%–40% | 0 |
| lower_nopunct | all_shuffled | 1 | 10 | 0 | 0% | 0%–28% | 0 |
| lower_nopunct | all_shuffled | 2 | 10 | 0 | 0% | 0%–28% | 0 |
| lower_nopunct | all_shuffled | 4 | 10 | 0 | 0% | 0%–28% | 0 |
| lower_nopunct | all_shuffled | 8 | 10 | 0 | 0% | 0%–28% | 0 |

## Completed-response sensitivity

Only cells containing an incomplete turn are shown. The scheduled denominator remains primary.

| variant | condition | N | scheduled semantic | completed-response semantic |
| :-- | :-- | --: | --: | --: |
| original | signal | 4 | 4/10 | 4/9 |
| original | all_shuffled | 1 | 0/10 | 0/7 |
| original | all_shuffled | 2 | 0/10 | 0/5 |
| original | all_shuffled | 4 | 0/10 | 0/6 |
| lower | all_shuffled | 2 | 0/10 | 0/9 |
| lower | all_shuffled | 4 | 1/10 | 1/9 |
| lower | all_shuffled | 8 | 0/10 | 0/8 |
| nopunct | signal | 8 | 2/10 | 2/9 |
| nopunct | all_shuffled | 1 | 0/10 | 0/8 |
| nopunct | all_shuffled | 4 | 0/10 | 0/6 |
| lower_nopunct | all_shuffled | 2 | 0/10 | 0/9 |

## Normalization interaction

Positive difference-in-differences means normalization reduced all-shuffled success more than signal success.

| variant | N | Δ signal | Δ all shuffled | interaction | bootstrap 95% CI |
| :-- | --: | --: | --: | --: | :-- |
| lower | 1 | +0% | +0% | +0% | +0%–+0% |
| lower | 2 | -50% | +0% | -50% | -80%–-20% |
| lower | 4 | -30% | +10% | -40% | -70%–-10% |
| lower | 8 | -30% | -30% | +0% | -60%–+60% |
| nopunct | 1 | +0% | +0% | +0% | +0%–+0% |
| nopunct | 2 | -50% | +0% | -50% | -80%–-20% |
| nopunct | 4 | +10% | +0% | +10% | -30%–+50% |
| nopunct | 8 | -20% | -20% | +0% | -60%–+60% |
| lower_nopunct | 1 | +0% | +0% | +0% | +0%–+0% |
| lower_nopunct | 2 | -60% | +0% | -60% | -90%–-30% |
| lower_nopunct | 4 | -20% | +0% | -20% | -60%–+20% |
| lower_nopunct | 8 | -30% | -30% | +0% | -50%–+50% |

## Computational effort

Medians exclude missing usage from incomplete turns. Timeouts remain in timeout counts and elapsed-time medians. Full N-level metrics are in `effort-summary.csv`.

| variant | condition | semantic | timeouts | tool trials | shell trials | median elapsed (s) | median input tokens | median reasoning tokens |
| :-- | :-- | --: | --: | --: | --: | --: | --: | --: |
| original | signal | 28/40 | 1 | 8 | 8 | 51.5 | 14129 | 2112 |
| original | all_shuffled | 3/40 | 12 | 14 | 12 | 427.4 | 15037 | 9242 |
| lower | signal | 17/40 | 0 | 5 | 5 | 55.3 | 14128 | 2552 |
| lower | all_shuffled | 1/40 | 4 | 13 | 10 | 182.9 | 15033 | 8698 |
| nopunct | signal | 22/40 | 1 | 13 | 11 | 82.4 | 13623 | 3812 |
| nopunct | all_shuffled | 1/40 | 6 | 19 | 17 | 481.5 | 137259 | 14261 |
| lower_nopunct | signal | 17/40 | 0 | 8 | 6 | 62.7 | 14010 | 2578 |
| lower_nopunct | all_shuffled | 0/40 | 1 | 18 | 14 | 317.5 | 32684 | 13799 |

Across variants, all-shuffled trials produced 23/160 timeouts and tool use in 64/160 trials, versus 2/160 timeouts and tool use in 34/160 signal trials.
The largest cell median input context was 353330 tokens for lower_nopunct / all_shuffled / N=2.

## Trace-derived strategies

Strategy labels describe only observable JSONL events. They do not expose private chain-of-thought.

| condition | semantic success | observable primary strategy | trials |
| :-- | :-- | :-- | --: |
| signal | yes | direct_one_pass_response | 62 |
| signal | yes | explicit_fixed_stride_hypothesis | 16 |
| signal | yes | explicit_recognition_of_shuffled_text | 2 |
| signal | yes | explicit_testing_of_candidate_strides | 2 |
| signal | yes | shell_or_tool_assisted_reconstruction | 2 |
| signal | no | apparent_lexical_reconstruction | 1 |
| signal | no | direct_one_pass_response | 40 |
| signal | no | explicit_fixed_stride_hypothesis | 14 |
| signal | no | explicit_recognition_of_shuffled_text | 10 |
| signal | no | shell_or_tool_assisted_reconstruction | 11 |
| all_shuffled | yes | direct_one_pass_response | 1 |
| all_shuffled | yes | explicit_fixed_stride_hypothesis | 2 |
| all_shuffled | yes | explicit_testing_of_candidate_strides | 2 |
| all_shuffled | no | apparent_lexical_reconstruction | 9 |
| all_shuffled | no | direct_one_pass_response | 50 |
| all_shuffled | no | explicit_fixed_stride_hypothesis | 30 |
| all_shuffled | no | explicit_recognition_of_shuffled_text | 24 |
| all_shuffled | no | explicit_testing_of_candidate_strides | 8 |
| all_shuffled | no | shell_or_tool_assisted_reconstruction | 34 |

The finer variant-by-condition strategy table is in `strategy-summary.csv`.

| variant | condition | strategy | trials |
| :-- | :-- | :-- | --: |
| original | signal | direct_one_pass_response | 27 |
| original | signal | explicit_fixed_stride_hypothesis | 8 |
| original | signal | explicit_recognition_of_shuffled_text | 1 |
| original | signal | explicit_testing_of_candidate_strides | 2 |
| original | signal | shell_or_tool_assisted_reconstruction | 2 |
| original | all_shuffled | apparent_lexical_reconstruction | 4 |
| original | all_shuffled | direct_one_pass_response | 14 |
| original | all_shuffled | explicit_fixed_stride_hypothesis | 13 |
| original | all_shuffled | explicit_recognition_of_shuffled_text | 2 |
| original | all_shuffled | explicit_testing_of_candidate_strides | 4 |
| original | all_shuffled | shell_or_tool_assisted_reconstruction | 3 |
| lower | signal | apparent_lexical_reconstruction | 1 |
| lower | signal | direct_one_pass_response | 28 |
| lower | signal | explicit_fixed_stride_hypothesis | 6 |
| lower | signal | explicit_recognition_of_shuffled_text | 3 |
| lower | signal | shell_or_tool_assisted_reconstruction | 2 |
| lower | all_shuffled | apparent_lexical_reconstruction | 2 |
| lower | all_shuffled | direct_one_pass_response | 16 |
| lower | all_shuffled | explicit_fixed_stride_hypothesis | 5 |
| lower | all_shuffled | explicit_recognition_of_shuffled_text | 7 |
| lower | all_shuffled | explicit_testing_of_candidate_strides | 1 |
| lower | all_shuffled | shell_or_tool_assisted_reconstruction | 9 |
| nopunct | signal | direct_one_pass_response | 23 |
| nopunct | signal | explicit_fixed_stride_hypothesis | 9 |
| nopunct | signal | explicit_recognition_of_shuffled_text | 3 |
| nopunct | signal | shell_or_tool_assisted_reconstruction | 5 |
| nopunct | all_shuffled | apparent_lexical_reconstruction | 2 |
| nopunct | all_shuffled | direct_one_pass_response | 10 |
| nopunct | all_shuffled | explicit_fixed_stride_hypothesis | 11 |
| nopunct | all_shuffled | explicit_recognition_of_shuffled_text | 5 |
| nopunct | all_shuffled | explicit_testing_of_candidate_strides | 2 |
| nopunct | all_shuffled | shell_or_tool_assisted_reconstruction | 10 |
| lower_nopunct | signal | direct_one_pass_response | 24 |
| lower_nopunct | signal | explicit_fixed_stride_hypothesis | 7 |
| lower_nopunct | signal | explicit_recognition_of_shuffled_text | 5 |
| lower_nopunct | signal | shell_or_tool_assisted_reconstruction | 4 |
| lower_nopunct | all_shuffled | apparent_lexical_reconstruction | 1 |
| lower_nopunct | all_shuffled | direct_one_pass_response | 11 |
| lower_nopunct | all_shuffled | explicit_fixed_stride_hypothesis | 3 |
| lower_nopunct | all_shuffled | explicit_recognition_of_shuffled_text | 10 |
| lower_nopunct | all_shuffled | explicit_testing_of_candidate_strides | 3 |
| lower_nopunct | all_shuffled | shell_or_tool_assisted_reconstruction | 12 |

## Observable unusual behavior counts

- Timeout/nonresponse runner events: 25
- Final responses explicitly mentioning shuffle/encoding: 87
- Responses with malformed object substitutions: 24
- Correct signal trials with a direct/no-tool/no-explicit-reconstruction primary trace label: 62/84
- Correct signal trials with any observable tool call: 11/84
- Correct all-shuffled trials with any observable tool call: 4/5
- Some timed-out traces ended on progress messages after recognizing the task or scrambling; those are not final task successes.
- Several failures substituted material/object pairs such as `brass coin` or `silver key`, consistent with lexical recombination rather than reliable relational recovery.

## Conclusion and next step

The preregistered directional hypothesis was not supported. Normalization did eliminate or reduce the original N=8 all-shuffled successes, but it generally damaged intact-signal recovery as much or more; the paired interaction estimates were zero or negative in most cells. The result therefore does not isolate punctuation/capitalization as a cue used disproportionately for unordered reconstruction.

The fully instrumented replication did reproduce robust blind task recovery and substantial run-to-run variability. Observable traces separate many cheap direct responses from expensive tool-assisted reconstruction, but a direct final response cannot establish implicit decoding because the payload itself suppresses explanation.

Proceed to the preregistered equal-multiset A/B Experiment 2 without changing its central design. Its answer-identity endpoint is more discriminating than another success-rate comparison. Retain full traces, the explanation-permitted arm, and the tool-less regime so that ordered-channel sensitivity can be separated from explicit agentic reconstruction.

## Interpretation boundary

Correct all-shuffled answers are not periodic-lane recovery. Final-answer silence about encoding is not evidence that encoding was not consciously discovered, especially because the payload suppresses explanation. Statistical summaries describe repeatability for this model/runtime rather than classical population inference.
