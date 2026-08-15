# Minimal external replication

This packet reproduces the paper's two strongest equal-bag conditions without
requiring the project's exploratory history. It contains exact byte copies of
frozen prompts from Experiment 2 and Experiment 4A.

## Frozen slate

The selection rule was fixed before external execution and does not use
historical outcomes:

| Study | Signal prompts | Paired seeds | Shuffled controls |
| --- | ---: | ---: | ---: |
| Experiment 2, N=2 | 20 | 10 | 10 |
| Experiment 4A, uniform 50% | 20 | 10 | 5 |
| **Total** | **40** | **20** | **15** |

For each signal cohort, seeds 1–10 are used. Experiment 2 uses controls 1–10;
Experiment 4A uses all five frozen controls. Trial order is a deterministic
SHA-256 ordering of neutral logical IDs, independent of prior success.

## Quick start

Validate prompt hashes without invoking a model:

```bash
python3 -B replication/validate_packet.py
python3 -B replication/run-core-replication.py --dry-run
```

Run a model command that accepts exactly one prompt on standard input and emits
one final response on standard output:

```bash
python3 -B replication/run-core-replication.py \
  --results-dir replication/external-results \
  -- your-model-command --model MODEL --reasoning medium
```

Then score:

```bash
python3 -B replication/score-core-replication.py \
  replication/external-results
```

The runner passes only prompt text to the command. It does not pass condition,
seed, expected identity, source filename, or answer key. See `PROTOCOL.md` for
freezing, retry, and reporting rules.

The command argv is preserved in each result record for provenance. Do not put
credentials directly in command-line arguments; use the model runtime's normal
credential store or environment mechanism, and never commit credentials.

## Files

- `execution-manifest.json`: neutral runtime order, hashes, and word counts.
- `provenance-manifest.json`: post-run audit trail to original frozen prompts.
- `scoring-key.json`: answer identities; never expose this to subject context.
- `packet-freeze.json`: aggregate prompt-set and manifest hashes.
- `frozen-prompts/`: exact prompt bytes.
- `run-core-replication.py`: runtime-neutral prompt-to-response harness.
- `score-core-replication.py`: answer-identity and paired scoring.
- `expected-schema.json`: JSON Schema for individual runtime records.

This package does not require Codex orchestration. A fresh direct model call per
prompt is preferred. Do not silently substitute a different model or reasoning
setting; an unavailable configuration remains unavailable.
