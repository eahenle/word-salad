# Five-symbol task v1: failed clean validation

The preregistered clean gate failed decisively:

| identity | normalized exact | required |
| --- | ---: | ---: |
| A | 0/20 | at least 18/20 |
| B | 0/20 | at least 18/20 |

All 40 subjects completed without runner error or timeout and returned a
five-name permutation, so this is not a transport failure or missing-response
artifact. All exposed reasoning-token counts were zero. Wrong outputs were
highly concentrated rather than uniformly random, including one output in 13/20
A trials and another in 8/20 B trials.

The scorer was audited against the frozen raw responses and the deterministic
simulator; no expected sequence appeared. The task used “rotate ... left,” whose
operational interpretation may be ambiguous or unreliable for the model. The
protocol therefore prohibits running the already-frozen scrambled cohort or any
buried-signal trial with task v1.

Task v1 remains immutable. A new version may replace rotation with two explicit,
overlapping positional swaps and must independently pass the same 20 A / 20 B
clean gate before interference.
