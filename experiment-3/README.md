# Experiment 3: frequency jitter and capability scaling

Experiment 3 tests how recovery of the frozen Experiment 2 equal-word-multiset
A/B payloads changes when the fixed positional clock is destroyed, and how that
behavior scales across model family and reasoning effort.

Experiments 1C and 2 are immutable inputs. Their active datasets are not
regenerated, rescored, or modified. Experiment 3 uses fresh Docker-isolated
Codex subjects only. Direct API calls are not planned or authorized.

## Frozen references

- Experiment 1C: tag `experiment-1c-hardened-normalization`, commit
  `389970d43bc8a490d699322afcfa31a41775f975`.
- Experiment 2: tag `experiment-2-toolless-cost-truncated-pilot`, commit
  `802619e47ab60d6b06162a582416cfa867457ffa`.
- Experiment 2 constrained payloads contain 161 words each, have exactly equal
  whitespace-delimited multisets, and yield distinct A/B answers.

The handoff described 196 signal words and 392 total positions. That conflicts
with the frozen payload, which has 161 words. This protocol preserves the
payload rather than padding or redesigning it: every N=2 stimulus therefore has
161 signal words, 161 distractor words, and 322 total positions.

## Preregistered hypotheses

### H1: fixed-clock dependence

If recovery substantially depends on a periodic residue class, paired recovery
will be higher under the fixed carrier than under jitter.

### H2: general sparse source separation

If coherent language can be separated without a fixed clock, fixed and jitter
paired recovery will be similar.

### H3: capability compensation

If irregular recovery is inference-computation limited, the jitter penalty will
decrease with model strength and/or reasoning effort.

These hypotheses and the prompt hash manifest are frozen before behavioral
scoring.

## Carrier construction

Carrier masks are binary sequences independent of lexical content: `S` consumes
the next ordered signal word and `D` consumes the next distractor word.

The fixed carrier uses alternating `S D` or its phase-inverted equivalent. The
balanced jitter carrier uses 160 signal-to-signal intervals: 80 of length 1 and
80 of length 3, permuted deterministically by seed. For phase 0, the first
signal is at position 0 and the last at position 320, leaving a distractor at
position 321—exactly the fixed phase-0 boundaries. Phase 1 uses the reversed
mask, matching fixed phase-1 boundaries. Both carriers preserve 50% density,
322 words, identical signal and distractor streams, and identical aggregate
word bags. The jitter carrier is not periodic.

Matched A/B prompts use the same phase, carrier mask, and distractor source-index
permutation. The fixed prompts are byte-identical to the constrained N=2
Experiment 2 prompts. All-shuffled controls use the jitter mask but replace the
ordered stream with another independent source-index permutation.

## Staged execution

1. Generate and validate all 83 frozen stimuli: 20 fixed A/B pairs, 20 jitter
   A/B pairs, and three jitter-mask all-shuffled controls.
2. Validate the pinned hardened container boundary.
3. Run 12 exact model/reasoning capability probes without substitution.
4. Run the Sol-xhigh anchor: the preregistered resource-pressure minimum of 10
   fresh jitter A/B pairs and three controls. Reuse the exact matched 10 fixed
   A/B pairs from Experiment 2. This preserves quota for the capability matrix.
5. Freeze and score the anchor before launching the common matrix.
6. For each supported configuration, screen the same first 10 fixed pairs,
   first 10 jitter pairs, and three controls. Reuse the anchor/reference cell.
7. Expand only scientifically informative boundary cells using whole fresh-seed
   cohorts.

The capability probe completed successfully for all 12 exact cells on the
pinned Codex runtime; no substitutions were made. The frozen Sol-xhigh anchor
recovered 13/20 expected fixed answers (5/10 complete A/B pairs) and 17/20
expected jitter answers (7/10 complete pairs). None of the three all-shuffled
controls produced target A/B output; one reached the preregistered 900-second
timeout. These screening data reject a jitter-collapse stopping rule and justify
running the common matrix, but the apparent 20-point paired jitter advantage is
too imprecise to interpret as a real improvement.

The common screening matrix is frozen in `results/screening-freeze.json` and
contains 473 new trials plus the 43-result Sol-xhigh reference cell. Across all
12 configurations, fixed carriers produced 69/240 expected individual answers
and 17/120 complete A/B pairs; balanced jitter produced 95/240 and 31/120.
The matched discordances favored jitter at both the individual and paired
levels. No all-shuffled control produced answer A or B.

This rules out a necessary constant period-2 clock for this construction. It
does not yet establish robustness to arbitrary placement: the balanced 1/3
interval mask creates adjacent signal-word bursts. The frozen confirmation plan
therefore expanded only Sol-medium, Terra-xhigh, and Spark-xhigh on seeds 11–20.
It did not expand controls or the remaining nine matrix cells. The 120 fresh
confirmation trials were frozen before scoring in
`results/confirmation-freeze.json`; all completed without timeout or runner
error.

In the fresh confirmation half, fixed carriers produced 21/60 expected answers
and 8/30 complete pairs, versus 23/60 and 9/30 for jitter. Cumulatively over 20
paired seeds in the selected cells, Sol-medium reached 10/20 fixed and 12/20
jitter pairs; Terra-xhigh reached 2/20 and 6/20; Spark-xhigh reached 0/20 and
0/20. Spark's single screening jitter answer did not replicate. The targeted
confirmation therefore preserves the no-jitter-collapse conclusion while
shrinking the apparent advantage in the fresh half.

Post-freeze semantic scoring accepts both the requested object-to-color format
and an unambiguous inverse box-to-contents format. Contradictory duplicate
placements are not normalized into a success. Observable trace strategy is a
separate endpoint and never claims access to private chain of thought.

The requested matrix is:

| model | medium | high | xhigh |
| --- | --- | --- | --- |
| `gpt-5.6-sol` | probe/run | probe/run | probe/reference |
| `gpt-5.6-terra` | probe/run | probe/run | probe/run |
| `gpt-5.6-luna` | probe/run | probe/run | probe/run |
| `gpt-5.3-codex-spark` | probe/run | probe/run | probe/run |

An unsupported or unavailable cell remains missing. No model or reasoning level
is substituted. OpenAI's model catalog documents medium/high/xhigh for the
GPT-5.6 family and medium/high/xhigh for GPT-5.3-Codex; the exact Spark Codex
alias is nevertheless probed empirically because catalog support does not prove
availability to this Codex account/runtime.

## Hardened execution boundary

Every fresh subject receives a new read-only container and new tmpfs instances
for `/subject`, `/tmp`, and `/codex-home`. No host path is mounted. The sole
user-level input is the stimulus passed on stdin. The pinned image and credential
gate are inherited from Experiments 1C/2. Model-generated shell commands run as
the unprivileged `subject` user with no effective capabilities and
`NoNewPrivs=1`; the root-only credential tmpfs is unreadable to that shell.

Full stdout JSONL, stderr, final response, thread ID, usage, tool calls, command
outputs, elapsed time, exit status, timeout state, and hashes are preserved.
Traces are analyzed only after a cohort is behaviorally frozen. Same-host Docker
is an audited practical isolation boundary, not a cryptographic multi-host
guarantee.

## Preparation commands

```bash
python3 -B experiment-3/generate.py
python3 -B experiment-3/validate.py
python3 -B experiment-3/reuse_fixed.py
python3 -B experiment-3/validate_isolation.py \
  --auth /path/to/auth.json
python3 -B experiment-3/capability_probe.py \
  --auth /path/to/auth.json
python3 -B experiment-3/run_codex.py \
  --auth /path/to/auth.json --model gpt-5.6-sol --reasoning xhigh \
  --carriers jitter all-shuffled --seeds 1 2 3 4 5 6 7 8 9 10
python3 -B experiment-3/freeze_cohort.py --cohort anchor
python3 -B experiment-3/score.py \
  --model gpt-5.6-sol --reasoning xhigh --build-anchor
python3 -B experiment-3/analyze_anchor.py
```

No scoring command should be run until the corresponding execution cohort has
been frozen.

## Completed artifacts

The screening report is `results/analysis.md`; the preregistered targeted
confirmation is `results/confirmation-analysis.md`. Machine-readable answer,
effort, strategy, confidence-interval, and matched-comparison outputs accompany
those reports. `results/integrity-audit.json` verifies prompt and trace hashes,
Docker isolation, frozen prior worktrees, infrastructure-error absence, and zero
direct API calls. `results/experiment-freeze.json` closes the dataset; the
immutable repository reference is tag `experiment-3-frequency-jitter-scaling`.
