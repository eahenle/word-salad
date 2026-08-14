# Experiment 3 targeted confirmation

## Result

The preregistered fresh-seed confirmation produced 21/60 fixed and 23/60 jitter expected individual answers, with 8/30 versus 9/30 complete A/B pairs. Thus the large screening-wide jitter advantage narrowed in these three confirmation cells, but it did not reverse.

Across screening plus confirmation for the selected cells, the matched fresh-seed comparison contained 6 fixed-only and 12 jitter-only paired successes (exact McNemar p=0.2379). This is a repeatability summary, not population inference over models.

## Fresh and cumulative cells

| model | cohort | fixed individual | fixed pairs | jitter individual | jitter pairs | paired jitter penalty | counterpart errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Sol-medium | confirmation | 14/20 | 6/10 | 14/20 | 6/10 | 0% | 1 |
| Sol-medium | cumulative | 25/40 | 10/20 | 30/40 | 12/20 | -10% | 2 |
| Terra-xhigh | confirmation | 7/20 | 2/10 | 9/20 | 3/10 | -10% | 1 |
| Terra-xhigh | cumulative | 13/40 | 2/20 | 19/40 | 6/20 | -20% | 3 |
| Spark-xhigh | confirmation | 0/20 | 0/10 | 0/20 | 0/10 | 0% | 0 |
| Spark-xhigh | cumulative | 0/40 | 0/20 | 1/40 | 0/20 | 0% | 0 |

Sol-medium replicated robust recovery: its confirmation half was tied at 6/10 pairs for each carrier, and its cumulative result was 10/20 fixed versus 12/20 jitter pairs. Terra-xhigh retained the predicted direction at 2/10 versus 3/10 fresh pairs and 2/20 versus 6/20 cumulatively. Spark-xhigh produced no confirmation success; cumulatively it had one jitter individual answer and no complete pair. The Spark boundary therefore replicated as essentially absent recovery.

## Effort and observable strategy

No confirmation trial timed out or had a runner/infrastructure error. Median time and reasoning-token values are preserved per cell in `confirmation-summary.csv`.

Across all 88 successful selected-cell signal trials from seeds 1–20, observable strategies were: `direct_one_pass_tool_free` 83, `explicit_fixed_stride_recognition` 2, `explicit_stride_testing` 2, `repeated_reconstruction` 1. These labels use only emitted events; they do not expose private chain of thought.

The primary successful mode remained direct and tool-free. Specific stride or jitter discovery is counted only when a trace contains concrete emitted evidence, never inferred from a terse correct answer.

## Interpretation

The confirmation supports the screening conclusion that a strict period-2 clock is not necessary for this task. It does not establish recovery under arbitrary irregular placement: the balanced jitter mask contains adjacent signal-word bursts, a plausible local-coherence advantage. Reasoning effort was nonmonotonic in screening, while confirmation reinforces a strong family-level boundary: Sol succeeds reliably, Terra partially, and Spark effectively not at all.

The most discriminating next experiment is a small, preregistered uniform-random-placement comparison in Sol-medium and Terra-xhigh. That should be a new frozen experiment, not an extension of this dataset.
