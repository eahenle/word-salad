# Historical trace-awareness audit

This post-freeze audit scans active subject traces from Experiments 1B through
4C.2 for spontaneous language about hidden messages, interleaving, positional
structure, reconstruction, encoding, signal/noise, and shuffled text.

It deliberately distinguishes three situations:

1. visibly multiplexed or scrambled stimuli, where structural language is
   directly suggested by what the subject sees;
2. natural but evaluation-like prose from the 4B.1 pilot, where `marker tool`,
   color labels, recording language, and requested summaries are locally
   visible confounds;
3. ordinary coherent prose and unrelated contamination probes, where
   spontaneous interleaving language would be substantially more suspicious.

Only completed observable trace items are scanned: agent messages, emitted
reasoning text where present, shell commands and outputs, and web-search text.
The scanner does not claim access to private chain of thought.

Run:

```text
python3 scan.py
```

Outputs:

- `awareness-occurrences.jsonl`: every matched occurrence plus the exact prompt;
- `awareness-timeline.csv`: one row per affected trial;
- `summary.json`: cohort and term counts;
- `analysis.md`: evidence-weighted interpretation.

Invalidated runtime/method attempts, isolation checks, smoke tests, capability
probes, and non-subject result JSONL files are excluded by explicit cohort
routing.
