# Five-symbol task v2: clean-valid but control-contaminated

## Clean execution

| identity | normalized exact | required |
| --- | ---: | ---: |
| A | 20/20 | at least 18/20 |
| B | 20/20 | at least 18/20 |

The positional-swap redesign fully repaired the v1 execution failure.

## N=1 scrambled control

Two of ten independently shuffled task word bags produced the exact target-A
sequence `Birch Dune Cobalt Aster Ember`. No control produced target B.

| endpoint | result |
| --- | ---: |
| any target sequence | 2/10 |
| target A | 2/10 |
| target B | 0/10 |
| runner errors | 0/10 |
| timeouts | 0/10 |

The two preregistered targets occupy 2/120 possible five-symbol permutations,
but model outputs are not uniformly random over that space. The observed
target-A concentration demonstrates an order-independent reconstruction or
response-bias path for this task wording.

The preregistered scrambled gate therefore failed. No v2 25% or 50% carrier
prompt was generated or run. Per the publication stop condition, task redesign
ends here; the paper should rely on the robust Experiments 2–4A core and report
Experiment 6 as a transparent measurement-instrument failure.
