# Sol-xhigh jitter anchor

Behavior was scored after the cohort freeze and before trace strategy analysis.

| carrier | scheduled | completed | timeouts | expected | target A/B |
| --- | ---: | ---: | ---: | ---: | ---: |
| fixed | 20 | 20 | 0 | 13 | 14 |
| jitter | 20 | 20 | 0 | 17 | 17 |
| all-shuffled | 3 | 2 | 1 | 0 | 0 |

| carrier | pairs | both expected | paired rate [95% Wilson CI] |
| --- | ---: | ---: | --- |
| fixed | 10 | 5 | 50.0% [23.7%, 76.3%] |
| jitter | 10 | 7 | 70.0% [39.7%, 89.2%] |

Paired jitter penalty: -20.0%.

The manipulation is retained for the common matrix. This is a staged
screening decision, not a final mechanistic conclusion.
