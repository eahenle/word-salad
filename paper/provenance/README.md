# Provenance index

Core frozen tags:

- `experiment-1c-hardened-normalization`
- `experiment-2-pilot`
- `experiment-2-toolless-cost-truncated-pilot`
- `experiment-3-frequency-jitter-scaling`
- `experiment-4a-uniform-random`
- `experiment-4c-dual-channel-negative-gate`
- `experiment-4c1-foreground-coherence-null`
- `experiment-4c2-density-125-control-stop`
- `experiment-5-cloud-context-audit-negative`
- `experiment-5-trace-awareness-audit`
- `experiment-5-balanced-density-frozen`
- `experiment-6-five-symbol-protocol`
- `experiment-6-five-symbol-v1-clean-failed`
- `experiment-6-five-symbol-v2-clean-protocol`
- `experiment-6-five-symbol-v2-clean-validated`
- `experiment-6-five-symbol-v2-scrambled-protocol`
- `experiment-6-five-symbol-v2-control-stop`

Experiment directories contain exact image IDs, prompt hashes, runtime hashes,
execution freezes, isolation audits, and invalidated-attempt records. This index
is machine-checked into `frozen-tags.csv`; source hashes used for the paper
summary are stored in `../publication-summary.json`.

The corrected evidence layer adds:

- `publication-number-audit.json`: 43 frozen-source consistency checks;
- `evidence-freeze.json`: hashes for generated tables, figures, claims,
  outline, methods skeleton, and analysis scripts;
- `runtime-images.csv`: pinned subject-image provenance.
