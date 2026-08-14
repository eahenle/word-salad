# Experiment 4A: uniform-random carrier

Experiment 4A tests whether the frozen equal-multiset Experiment 2 A/B messages
remain recoverable when ordered signal positions are sampled uniformly without
replacement. There is no fixed stride, balanced-gap schedule, boundary
conditioning, or mask rejection based on run structure.

Experiments 1C, 2, and 3 are immutable inputs. Their prompts, traces, scores,
and analyses are never regenerated or modified. Experiment 4A uses only fresh,
Docker-isolated Codex subjects and makes no direct API calls.

## Frozen references and count correction

- Experiment 3 tag: `experiment-3-frequency-jitter-scaling`, commit
  `b3bd850e3e03c87eb0b7ba6a2d97c3653472eca3`.
- Experiment 2/3 payload A and B each contain 161 whitespace-delimited words,
  not the 196 stated in the handoff.
- Preserving the frozen payload is scientifically necessary. Each uniform
  prompt therefore contains 161 signal words, 161 distractor words, and 322
  total positions. No padding or payload redesign is permitted.

## Preregistered construction

For seed `s`, a deterministic PRNG seeded through a versioned SHA-256-derived
seed samples exactly 161 distinct positions from `range(322)`. The positions
are sorted; successive ordered payload words occupy those positions. The other
positions receive the exact distractor source-index permutation used by the
matched Experiment 3 fixed and jitter prompt.

Paired A/B prompts use the identical mask and distractor permutation. No mask
is rejected because of its first or last position, run lengths, adjacency, gap
variance, apparent structure, or awkward local wording. All-shuffled controls
use the same construction with an independently shuffled signal stream.

## Preregistered cohort and stopping rule

Primary cells:

- `gpt-5.6-sol`, reasoning `medium`;
- `gpt-5.6-terra`, reasoning `xhigh`.

Each cell receives 20 paired A/B seeds (40 signal prompts) and five
all-shuffled controls. The scheduled total is 90 subject trials. If Codex quota
or capacity pressure materially prevents completion, execution may stop only
at the common 10-seed boundary after both model cells have the same signal
seeds and all controls. This decision must be made without inspecting response
or trace content. Timeouts are data and are not retried. Broken pipes,
connection resets, or equivalent infrastructure failures are retry-eligible
for the specific affected trial and must remain documented.

## Hypotheses and endpoints

The primary endpoint is complete paired discrimination: A produces answer A
and B produces answer B for the same seed. Individual expected-answer recovery
is secondary.

- Strong survival supports ordered linguistic source separation without a
  fixed carrier or simple deterministic placement rule.
- Weaker nonzero recovery supports a facilitating role for carrier regularity
  or local clustering without making it necessary.
- Collapse supports dependence on exploitable balanced-jitter structure.

The primary comparison uses frozen Experiment 3 cumulative 20-seed fixed and
balanced-jitter results for the same two exact model/effort configurations.
Mask-statistic correlations are post hoc exploratory analyses.

## Isolation and freezing

Every subject runs in a fresh pinned read-only container with new tmpfs mounts,
no host/repository mount, no prior session, and only the stimulus on stdin.
Full stdout JSONL, stderr, final response, usage, tool events, timing, errors,
and hashes are preserved. Same-host Docker is an audited practical boundary,
not a cryptographic multi-host guarantee.

Prompt hashes and hypotheses are frozen before inference. Responses and traces
are not inspected until the complete execution cohort is frozen.

## Completed result

All 90 scheduled subjects completed without timeout or runner error. Sol-medium
recovered 30/40 individual answers and 13/20 complete A/B pairs; Terra-xhigh
recovered 16/40 and 5/20. The 10 all-shuffled controls produced no target A/B
answers. Against the same cells' frozen balanced-jitter results, uniform random
placement produced the same aggregate paired recovery (18/40) and a closely
matched individual rate (46/80 versus 49/80).

Every one of the 46 successful uniform signal trials was an observable direct,
one-pass, tool-free response. The result supports recovery of a coherent
ordered subsequence without a fixed clock or deliberately imposed jitter
schedule. It does not establish arbitrary density or a specific mechanism.

The full report is `uniform/results/analysis.md`; integrity and frozen hashes
are in `uniform/results/integrity-audit.json` and
`uniform/results/experiment-freeze.json`.
