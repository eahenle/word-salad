# Experiment 1A-R scoring audit

The 80 replication responses were scored only after all 80 subject attempts finished. A hash-randomized packet hid condition, lane count, seed, trial ID, and (trivially for this first slate) normalization variant during response review.

## Corrected strict-match convention

The first scoring pass mistakenly obtained its strict-match string from a frozen historical row marked exact. That historical convention included a terminal period. The current handoff's canonical answer has no terminal period.

The invalid first-pass output is preserved rather than overwritten:

- `invalidated-scoring-terminal-period.jsonl`
- `invalidated-blind-audit-terminal-period.jsonl`

The corrected `trials.jsonl` uses the handoff's canonical no-period string. This changes only `exact_success` and exact-versus-semantic-success category assignment. Semantic correctness is unchanged.

## Manual audit findings

All 80 last observable agent-message strings were inspected. Assignment extraction and all 31 semantic-success decisions were confirmed. Thirteen timed-out subjects emitted a progress-style agent message but no `turn.completed` event; none of those messages was semantically correct. They are retained for qualitative/strategy analysis but excluded from completed-response-only sensitivity analysis.

Before normalized subjects were launched, two qualitative rules were broadened and then applied consistently to this and all later variants:

- explicit descriptions of a transposed instruction block count as encoding discovery;
- state-tracking/ordered-move descriptions and multi-object material shorthand count as partial task recovery.

These changes affect qualitative categories only. They do not change exact or semantic success.

## Replication scoring totals

| condition | N | exact | semantic |
| :-- | --: | --: | --: |
| signal | 1 | 2/10 | 10/10 |
| signal | 2 | 6/10 | 10/10 |
| signal | 4 | 2/10 | 4/10 |
| signal | 8 | 1/10 | 4/10 |
| all shuffled | 1 | 0/10 | 0/10 |
| all shuffled | 2 | 0/10 | 0/10 |
| all shuffled | 4 | 0/10 | 0/10 |
| all shuffled | 8 | 3/10 | 3/10 |
