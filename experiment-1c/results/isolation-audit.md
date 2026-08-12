# Experiment 1C isolation and leakage audit

The complete 320-trial slate was audited only after every subject finished.
The raw traces show no observed access to the host repository, historical
trials, prior sessions, experiment documentation, or coordinator-side answer
key material.

## Findings

- 31/320 subjects issued an environment or host-path probe.
- 0/320 traces contain observable host-access evidence.
- 0/320 traces contain direct experiment-context leakage.
- 4/320 traces printed a clean reconstruction of the payload in shell output.
  Command provenance shows that these strings were derived from the supplied
  stimulus by stride/index analysis; they were not read from a host artifact.
- One subject discovered the Codex runtime's root-owned prompt staging file in
  `/subject`. Attempts to read it returned `Permission denied`. It then created
  its own readable working copy from text already present in its model context.
- Attempts to inspect root process memory/maps, root file descriptors, host
  paths, prior temporary files, and authentication material were unsuccessful.

The mechanical report is `leakage-trace-audit-summary.json`; per-trial flags and
hashes are in `leakage-trace-audit.jsonl`. The auditor distinguishes attempted
probes from successful access and treats reconstructed payload text as a
behavioral strategy marker, not leakage.

## Boundary

This is evidence about the observable same-host Docker boundary, not a
cryptographic proof of isolation. Subjects could see ordinary process metadata
inside their own container and retained network access required for inference.
No host filesystem was mounted. Model-generated shell commands ran as the
unprivileged `subject` user with no effective capabilities and `NoNewPrivs=1`;
the Codex coordinator and credential tmpfs remained root-only.
