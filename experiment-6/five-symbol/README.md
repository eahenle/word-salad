# Experiment 6: five-symbol publication-closing instrument

Experiment 6 closes the major measurement gap left by the three-symbol density
ladder. It first validates the hidden task in clean form, then validates its
scrambled word bag, and only then permits matched 25% and 50% carrier trials.

## Equal-bag task

The five symbols are `Aster`, `Birch`, `Cobalt`, `Dune`, and `Ember`. Each occurs
exactly once. A and B contain the same whitespace-delimited word multiset and
differ only in the order of two noncommuting positional operations.

```text
A -> Birch Cobalt Aster Ember Dune
B -> Ember Cobalt Dune Birch Aster
```

The two targets occupy 2 of 120 possible five-symbol permutations.

## Frozen gates

1. **Clean execution:** 20 A and 20 B fresh Sol-medium subjects. Each identity
   must produce at least 18/20 normalized-exact five-name outputs.
2. **Scrambled N=1 control:** 10 independently shuffled copies of the same task
   word bag. No response may contain either complete target ordering.
3. **Discovery:** only after both gates pass, run matched A/B/scrambled cohorts
   at 25% and 50% density.
4. **Replication:** only a density with an interpretable discovery effect is
   eligible for one fresh independent replication.

Failure at either instrument-validation gate freezes this task version and stops
buried-signal execution. Ten-minute subject timeouts are outcomes. Only an
archived, demonstrably pre-response runner/transport/authentication failure is
eligible for an exact-prompt retry.

## Subjects

- `gpt-5.6-sol`, reasoning `medium`
- exact audited image
  `sha256:e04e78a7926fc489536fe595073b58888238bc4107a6fd5281047432031627da`
- fresh read-only Docker container and ephemeral Codex session per trial
- shell, filesystem, MCP, browser, apps, plugins, and other tool surfaces disabled
- no direct API billing

## Commands

```text
python3 generate_clean.py
python3 validate.py
python3 freeze_protocol.py
python3 validate_isolation.py
python3 run_cohort.py clean --auth /path/to/auth.json --workers 3 --timeout 600
python3 score_clean.py
```

Run the scrambled cohort only when `results/clean-gate.json` authorizes it.
