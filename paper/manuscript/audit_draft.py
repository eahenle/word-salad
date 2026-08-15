#!/usr/bin/env python3
"""Audit manuscript numeric statements against the frozen evidence layer."""

from __future__ import annotations

import json
import re
from pathlib import Path


MANUSCRIPT = Path(__file__).resolve().parent
PAPER = MANUSCRIPT.parent
RESULTS = MANUSCRIPT / "results.md"
METHODS = MANUSCRIPT / "methods.md"
CAPTIONS = MANUSCRIPT / "figure-captions.md"
REPORT = MANUSCRIPT / "draft-audit.json"


def main() -> None:
    evidence = json.loads((PAPER / "publication-summary.json").read_text())
    metrics = {
        (row["study"], row["endpoint"]): (row["successes"], row["trials"])
        for row in evidence["core_metrics"]
    }
    expected_metrics = {
        ("Experiment 2", "N=2 expected individuals"): (57, 80),
        ("Experiment 2", "N=2 complete A/B pairs"): (19, 40),
        ("Experiment 2", "N=4 expected individuals"): (33, 80),
        ("Experiment 2", "N=4 complete A/B pairs"): (8, 40),
        ("Experiment 2", "all-shuffled target answers"): (0, 80),
        ("Experiment 2 tool-less pilot", "N=2 expected individuals"): (35, 40),
        ("Experiment 2 tool-less pilot", "N=2 complete A/B pairs"): (16, 20),
        ("Experiment 3", "fixed expected individuals"): (69, 240),
        ("Experiment 3", "fixed complete A/B pairs"): (17, 120),
        ("Experiment 3", "jitter expected individuals"): (95, 240),
        ("Experiment 3", "jitter complete A/B pairs"): (31, 120),
        ("Experiment 4A", "uniform expected individuals"): (46, 80),
        ("Experiment 4A", "uniform complete A/B pairs"): (18, 40),
        ("Experiment 4A", "all-shuffled target answers"): (0, 10),
        ("Experiment 6 v2", "clean exact execution"): (40, 40),
        ("Experiment 6 v2", "scrambled target false positives"): (2, 10),
    }
    failures = []
    if metrics != expected_metrics:
        failures.append("publication-summary core metrics differ from audited expectations")
    text = RESULTS.read_text()
    normalized_text = re.sub(r"\s+", " ", text)
    required_fragments = [
        "22/40 signal trials and 0/40 all-shuffled controls",
        "80/160, compared with 2/160",
        "57/80 signal trials",
        "19/40 paired seeds",
        "33/80 trials",
        "8/40 complete pairs",
        "None of the 80 all-shuffled controls",
        "35/40 expected full answers",
        "16/20 complete A/B",
        "69/240 trials",
        "17/120 complete pairs",
        "95/240",
        "31/120",
        "30/40 expected individual answers and 13/20 complete A/B",
        "16/40 and 5/20",
        "46/80 individuals",
        "18/40 pairs",
        "All ten shuffled controls",
        "0/6 expected hidden answers and 0/3 complete pairs",
        "0/40 correct clean executions",
        "40/40 clean executions",
        "target A appeared in 2/10",
        "Exact recovery was 0/5",
    ]
    missing = [fragment for fragment in required_fragments if fragment not in normalized_text]
    if missing:
        failures.append("missing canonical Results fragments: " + repr(missing))
    combined = "\n".join(path.read_text() for path in (METHODS, RESULTS, CAPTIONS))
    normalized_combined = re.sub(r"\s+", " ", combined)
    if re.search(r"\b(?:196|392)\b", combined):
        failures.append("stale Experiment 4A geometry appears in manuscript")
    if "161 signal words, 161 distractor words, and 322 total positions" not in normalized_combined:
        failures.append("correct Experiment 4A geometry is absent")
    if "order-independent" in combined.lower():
        failures.append("overstrong Experiment 6 wording appears")
    if "no buried-signal trial using it was generated or run" not in normalized_text:
        failures.append("Experiment 6 no-execution statement is absent")
    report = {
        "schema_version": 1,
        "status": "pass" if not failures else "fail",
        "evidence_tag": "paper-evidence-freeze-v1",
        "files": [str(path.relative_to(PAPER.parent)) for path in (METHODS, RESULTS, CAPTIONS)],
        "checks": 7,
        "failures": failures,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    if failures:
        raise SystemExit("draft audit FAILED:\n- " + "\n- ".join(failures))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
