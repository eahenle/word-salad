# Experiment analysis

Rates use all scheduled trials as the denominator, including capped nonresponses. Intervals are 95% Wilson score intervals.

## Signal trials

| lanes | trials | exact success | semantic success | encoding discovered | nonresponses |
| ----: | -----: | ------------: | ---------------: | ------------------: | -----------: |
| 1 | 10 | 8 | 10 | 0 | 0 |
| 2 | 10 | 4 | 7 | 0 | 0 |
| 4 | 10 | 1 | 1 | 0 | 1 |
| 8 | 10 | 2 | 2 | 0 | 1 |

## All-shuffled controls

| lanes | trials | exact success | semantic success | encoding discovered | nonresponses |
| ----: | -----: | ------------: | ---------------: | ------------------: | -----------: |
| 1 | 10 | 0 | 0 | 0 | 3 |
| 2 | 10 | 0 | 0 | 0 | 2 |
| 4 | 10 | 0 | 0 | 1 | 4 |
| 8 | 10 | 1 | 3 | 2 | 1 |

## Classification totals

- `encoding_discovery_without_task_completion`: 3
- `exact_task_success`: 16
- `other`: 29
- `partial_recovery`: 25
- `semantic_task_success`: 7
