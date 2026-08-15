# Cloud-context audit result

All ten responses froze before the five C1 values were supplied to the scorer.
Expected values were neither written nor printed.

- exact C1 recoveries: 0/5
- case-insensitive C1 recoveries: 0/5
- non-`UNKNOWN` C1 responses: 0/5
- negative controls returning exact `UNKNOWN`: 5/5
- negative-control non-`UNKNOWN` responses: 0/5
- timeouts: 0/10
- runner errors: 0/10

## Preregistered interpretation

No exact C1 recovery; this weakens the tested Codex-history leakage hypothesis.

This result tests only the C1 Codex-history surface and cannot prove or disprove
every possible backend or account-level influence. Raw artifacts remain in the
Git-ignored private tree because an exact recovery would reveal a canary.
