#!/usr/bin/env python3
"""Freeze Experiment 3 execution cohorts before response scoring or trace review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from runtime import atomic_json, cell_slug


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root_default = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root_default)
    parser.add_argument("--cohort", required=True, choices=("anchor", "screening"))
    args = parser.parse_args()
    root = args.root
    if args.cohort == "anchor":
        slug = cell_slug("gpt-5.6-sol", "xhigh")
        expected_ids = {
            *(f"q{number:04d}" for number in range(41, 51)),
            *(f"q{number:04d}" for number in range(61, 71)),
            "q0081", "q0082", "q0083",
        }
        completed_dir = root / "completed" / slug
        files = sorted(completed_dir.glob("q*.json"))
        actual_ids = {path.stem for path in files}
        if actual_ids != expected_ids:
            raise RuntimeError(
                f"anchor IDs differ: missing={sorted(expected_ids-actual_ids)}, extra={sorted(actual_ids-expected_ids)}"
            )
        records = [json.loads(path.read_text()) for path in files]
        if any(record["model"] != "gpt-5.6-sol" or record["reasoning"] != "xhigh" for record in records):
            raise RuntimeError("anchor cell mismatch")
        if any(record["response"] is None for record in records):
            raise RuntimeError("anchor response field missing")
        reused = root / "results" / "reused-fixed-sol-xhigh.jsonl"
        record = {
            "cohort": "sol_xhigh_jitter_anchor",
            "status": "frozen_before_scoring_and_trace_analysis",
            "fresh_trial_ids": sorted(expected_ids),
            "fresh_trials": len(records),
            "fresh_trace_hashes": {
                path.stem: json.loads(path.read_text())["runner"]["trace_sha256"] for path in files
            },
            "reused_fixed_trials": 20,
            "reused_fixed_sha256": digest(reused),
            "response_text_inspected_before_freeze": False,
            "trace_content_inspected_before_freeze": False,
            "direct_api_calls": 0,
        }
    else:
        capability = json.loads((root / "results" / "capability-probe.json").read_text())
        supported = [cell for cell in capability["cells"] if cell["status"] == "supported"]
        expected_ids = {
            *(f"q{number:04d}" for number in range(1, 11)),
            *(f"q{number:04d}" for number in range(21, 31)),
            *(f"q{number:04d}" for number in range(41, 51)),
            *(f"q{number:04d}" for number in range(61, 71)),
            "q0081", "q0082", "q0083",
        }
        cells = {}
        for cell in supported:
            slug = cell_slug(cell["model"], cell["reasoning"])
            if slug == cell_slug("gpt-5.6-sol", "xhigh"):
                continue
            files = sorted((root / "completed" / slug).glob("q*.json"))
            actual = {path.stem for path in files}
            if actual != expected_ids:
                raise RuntimeError(f"{slug}: screening ID set differs")
            cells[slug] = {path.stem: json.loads(path.read_text())["runner"]["trace_sha256"] for path in files}
        if len(cells) != len(supported) - 1:
            raise RuntimeError("supported screening cell count mismatch")
        record = {
            "cohort": "common_model_reasoning_screening",
            "status": "frozen_before_comparative_scoring_and_trace_analysis",
            "fresh_cells": cells,
            "trials_per_fresh_cell": len(expected_ids),
            "sol_xhigh_source": "anchor plus reused fixed reference",
            "response_text_inspected_before_freeze": False,
            "trace_content_inspected_before_freeze": False,
            "direct_api_calls": 0,
        }
    path = root / "results" / f"{args.cohort}-freeze.json"
    if path.exists():
        raise FileExistsError(f"cohort already frozen: {path}")
    atomic_json(path, record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
