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
