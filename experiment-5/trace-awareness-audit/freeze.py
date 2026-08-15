#!/usr/bin/env python3
"""Freeze trace-audit inputs and generated outputs by hash."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scan import COHORTS, ROOT, REPO, trace_paths


EXPECTED_PARENT = "10a4501"
OUTPUTS = (
    "README.md", "scan.py", "analysis.md", "awareness-occurrences.jsonl",
    "awareness-timeline.csv", "summary.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    output = ROOT / "audit-freeze.json"
    if output.exists():
        raise RuntimeError("trace-awareness audit is already frozen")
    head = subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"], cwd=REPO,
        text=True, capture_output=True, check=True,
    ).stdout.strip()
    if head != EXPECTED_PARENT:
        raise RuntimeError(f"expected parent {EXPECTED_PARENT}, found {head}")
    summary = json.loads((ROOT / "summary.json").read_text())
    if summary["traces_scanned"] != 1709:
        raise RuntimeError("unexpected trace count")
    input_rows = []
    for cohort in COHORTS:
        for path in trace_paths(cohort):
            input_rows.append(f"{path.relative_to(REPO)}\t{sha256(path)}\n")
    combined = hashlib.sha256("".join(input_rows).encode()).hexdigest()
    freeze = {
        "schema_version": 1,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "git_commit_before_audit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO,
            text=True, capture_output=True, check=True,
        ).stdout.strip(),
        "cloud_context_audit_tag": "experiment-5-cloud-context-audit-negative",
        "input_trace_count": len(input_rows),
        "ordered_input_path_and_hash_manifest_sha256": combined,
        "output_hashes": {name: sha256(ROOT / name) for name in OUTPUTS},
        "summary_counts": {
            "traces_scanned": summary["traces_scanned"],
            "trials_with_awareness_terms": summary["trials_with_awareness_terms"],
            "observable_term_occurrences": summary["observable_term_occurrences"],
        },
        "invalidated_smoke_isolation_and_capability_traces_excluded": True,
        "private_chain_of_thought_available": False,
    }
    output.write_text(json.dumps(freeze, indent=2) + "\n")
    print(json.dumps(freeze, indent=2))


if __name__ == "__main__":
    main()
