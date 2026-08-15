# Statistical analysis

Primary reports use exact counts, Wilson binomial confidence intervals, paired
seed outcomes, matched discordances, and scheduled-trial denominators. P-values,
where shown, describe experimental repeatability for fixed runtime conditions and
are not treated as population inference over models.

Rebuild the publication artifacts from the repository root with:

```bash
python3 -B paper/statistical-analysis/build_paper.py
```

The builder asserts the headline Experiment 4A and Experiment 6 control counts,
copies frozen source tables, emits Wilson intervals, generates SVG figures, and
records SHA-256 hashes of every input used by the paper summary.

Run the independent fail-closed publication audit with:

```bash
python3 -B paper/statistical-analysis/audit_publication_numbers.py
```

It derives the cited counts from frozen Experiment 1C–6 artifacts, checks the
publication tables and prose guardrails, and writes the machine-readable report
under `paper/provenance/`. The `--freeze-manifest` flag additionally records
hashes of the evidence layer; use it only when creating a named evidence freeze.
