#!/usr/bin/env python3
"""Summarize all completed stages without changing any trial score."""

from __future__ import annotations

import csv
import io
import json

from generate import ROOT, STAGES
from runtime import atomic_bytes, atomic_json


def main() -> None:
    rows = []
    for stage, total_words in STAGES.items():
        path = ROOT / "stages" / stage / "results/development-gate.json"
        if not path.exists():
            continue
        gate = json.loads(path.read_text())
        rows.append({
            "stage": stage, "document_words": total_words,
            "density": 22 / total_words,
            "expected_individuals": gate["expected_individuals"],
            "signal_trials": gate["signal_trials"],
            "complete_ab_pairs": gate["complete_ab_pairs"],
            "total_pairs": gate["total_pairs"],
            "scrambled_target_selections": gate["scrambled_target_selections"],
            "scrambled_controls": gate["scrambled_controls"],
            "counterpart_errors": gate["counterpart_errors"],
            "recovery_gate_passed": gate["recovery_gate_passed"],
        })
    fields = list(rows[0]) if rows else []
    if rows:
        stream = io.StringIO(); writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
        atomic_bytes(ROOT / "results/density-summary.csv", stream.getvalue().encode())
    atomic_json(ROOT / "results/density-summary.json", {"completed_stages": rows})
    lines = ["# Balanced-density ladder\n", "| stage | density | expected | pairs | scrambled targets |", "| --- | ---: | ---: | ---: | ---: |"]
    for row in rows:
        lines.append(f"| {row['stage']} | {row['density']:.4f} | {row['expected_individuals']}/{row['signal_trials']} | {row['complete_ab_pairs']}/{row['total_pairs']} | {row['scrambled_target_selections']}/{row['scrambled_controls']} |")
    atomic_bytes(ROOT / "results/analysis.md", ("\n".join(lines) + "\n").encode())
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
