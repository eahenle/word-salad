# Experiment 1A-R and 1B: full traces and surface normalization

This directory is independent of the frozen historical experiment in `../multiplex-experiment/`. It contains an instrumented replication of the original multiplexing slate and a paired 2 × 2 case/punctuation matrix.

> **Invalidated same-host run:** The completed 320-trial dataset in this
> directory is preserved for forensic study but is not valid confirmatory
> evidence. Post-slate trace audit found that the inner `read-only` sandbox
> allowed reads outside the neutral working directory. Fourteen subjects left
> the intended filesystem boundary, eight obtained clean experiment material,
> and five surfaced the answer key from historical artifacts or prior Codex
> session logs. See `results/invalidation-report.md` and
> `results/leakage-trace-audit-summary.json`. Do not pool these results with a
> hardened rerun.

## Frozen baseline

The original Experiment 1A dataset is preserved at:

- commit: `395c9c615fe4bf8900b31b73c1071bab805682e6`
- annotated tag: `experiment-1a-original`

The tag was created before any Experiment 1B files were added. The historical prompts, results, metadata, scoring report, figures, and README are not regenerated, rescored, or edited by this pipeline.

Historical semantic-success context:

| condition | N=1 | N=2 | N=4 | N=8 |
| :-- | --: | --: | --: | --: |
| signal | 10/10 | 7/10 | 1/10 | 2/10 |
| all shuffled | 0/10 | 0/10 | 0/10 | 3/10 |

These values are comparison data, not replication targets.

## Experimental slate

The fully instrumented slate contains 320 fresh subjects:

- `original`: the 80-trial Experiment 1A-R replication;
- `lower`: lowercase with punctuation retained;
- `nopunct`: original case with Unicode punctuation removed;
- `lower_nopunct`: lowercase with Unicode punctuation removed.

Every variant uses signal and all-shuffled conditions, `N = 1, 2, 4, 8`, and seeds 1 through 10. The model is `gpt-5.6-sol` with `xhigh` reasoning. Official OpenAI documentation lists GPT-5.6 Sol and `xhigh` reasoning support: [model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [model guidance](https://developers.openai.com/api/docs/guides/latest-model).

## Pairing and normalization

`generate.py` first constructs each lane as a permutation of source-word indices using the frozen `q781-v1` algorithm. All four surface variants reuse that exact index geometry, phase, condition, lane count, and seed.

`normalize.py` renders indexed words afterward:

- lowercase uses Python `str.lower()`;
- punctuation stripping removes every character whose Unicode general category begins with `P`;
- whitespace is collapsed by joining rendered lexical units with one ASCII space;
- if a source word becomes empty, preflight fails instead of dropping it and changing the fixed stride.

Controls are judged intact primarily by source-index order. Preflight also rejects any shuffled lane that becomes rendered-identical to the normalized payload because distinct source words collapsed under normalization.

`validate.py` enforces lane multisets, aggregate multisets, signal extraction, no intact shuffled source-index lane, no rendered-equivalent control lane, identical geometry across variants, and SHA-256 prompt hashes. For `original`, all 80 prompt byte strings and permutations must match the frozen historical artifacts.

## Blind subject execution and raw traces

Each subject is a fresh ephemeral `codex exec --json` process with an empty neutral temporary working directory. The generated stimulus is its sole user-level input and is passed through stdin. No condition, variant, lane count, phase, filename, decoding hint, answer key, prior response, or trace is supplied.

The invocation uses:

```text
codex -m gpt-5.6-sol \
  -c 'model_reasoning_effort="xhigh"' \
  -s read-only -a never -C EMPTY_NEUTRAL_TEMP_DIR \
  exec --json --ephemeral --ignore-user-config --ignore-rules \
  --strict-config --skip-git-repo-check -
```

OpenAI's non-interactive-mode documentation states that `--json` makes stdout a JSONL stream containing every event Codex emits, including thread, turn, item, error, and completion events: [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

For every trial, the runner preserves:

- raw stdout bytes as `traces/qNNNN.jsonl`;
- raw stderr bytes separately;
- exit status and timeout state;
- elapsed wall time;
- thread ID and aggregate usage;
- the last observable `agent_message` (which is final only when the turn completes);
- event/item counts without discarding unknown event types;
- atomic attempt and completion records.

An existing attempt without a completion record is never retried implicitly. This avoids converting controller interruption into selective subject retries.

The scorer records any-message, `turn.completed`, completed-response, timeout, and no-message states separately. The trace archive contains only what the runtime emits. It does not expose private chain-of-thought or hidden system/developer context.

## Execution gates

Experiment 1A-R runs first and is scored only after all 80 subjects finish. The three normalized variants run afterward. Trace strategy analysis does not begin until the full 320-trial slate is complete, so observed strategies cannot alter execution midway.

Generate and validate Experiment 1A-R:

```bash
python3 generate.py --variants original
python3 validate.py --variants original
```

Run the 80-trial replication:

```bash
python3 run_experiment.py \
  --variants original \
  --model gpt-5.6-sol \
  --reasoning xhigh \
  --workers 4 \
  --timeout 900
```

After replication scoring/audit, validate and run the normalized matrix:

```bash
python3 validate.py --variants lower nopunct lower_nopunct
python3 run_experiment.py \
  --variants lower nopunct lower_nopunct \
  --model gpt-5.6-sol \
  --reasoning xhigh \
  --workers 4 \
  --timeout 900
```

Behavioral scoring is variant-agnostic and accepts the coordinator-only answer key only after subject execution:

```bash
export MULTIPLEX_ANSWER_KEY='<coordinator-only answer key>'
python3 score.py
```

Only after the complete matrix is frozen for scoring:

```bash
python3 trace_analysis.py
python3 analyze.py
```

## Scoring and analysis

The primary endpoint is semantic correctness. Scoring also records strict exact match, number of correct object assignments, malformed object substitutions, final-response encoding discovery, nonresponse, and a mutually exclusive behavioral category. A hash-randomized audit packet omits normalization, condition, lane count, seed, and trial identity to permit a practically variant-blind manual audit.

The analysis reports scheduled-denominator and completed-response-only rates, Wilson intervals, paired-seed normalization changes, difference-in-differences interactions, a ridge-stabilized categorical logistic model, computational-effort summaries, and observable trace-strategy categories.

Positive interaction means normalization reduced all-shuffled success more than signal success:

```text
(normalized signal − original signal)
− (normalized all-shuffled − original all-shuffled)
```

Regression and interval summaries characterize repeatability and effect magnitude for one model/runtime. They are not classical population inference.

## Intended isolation boundary and observed failure

See `leakage-audit.md` for the predeclared audit and post-run addendum. Empty working directories, neutral IDs, stdin-only prompts, ignored user/project rules, read-only sandboxes, ephemeral sessions, and separate post-hoc scoring reduced direct metadata exposure but did not create a read allowlist. The warned residual risk materialized: agents independently searched absolute host paths, repository files, historical temporary artifacts, and prior Codex session logs. A valid rerun requires an external filesystem boundary such as a container that mounts only a neutral work directory and minimal runtime credentials.

## Artifact layout

```text
experiment-1b/
├── README.md
├── leakage-audit.md
├── payload.txt
├── normalize.py
├── generate.py
├── validate.py
├── run_experiment.py
├── score.py
├── trace_analysis.py
├── analyze.py
├── audit.py
├── leakage_trace_audit.py
├── prompts/{original,lower,nopunct,lower_nopunct}/
├── metadata/{original,lower,nopunct,lower_nopunct}/
├── traces/
├── stderr/
├── attempts/
├── completed/
└── results/
```
