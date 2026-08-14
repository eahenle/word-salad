#!/usr/bin/env python3
"""Freeze the complete Experiment 4A execution cohort before scoring."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from runtime import CELLS, atomic_json, cell_slug


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent
    output = root / "uniform/results/execution-freeze.json"
    if output.exists():
        raise FileExistsError(f"cohort already frozen: {output}")
    expected = {f"q{number:04d}" for number in range(1, 46)}
    cells = {}
    for model, effort in CELLS:
        slug = cell_slug(model, effort)
        files = sorted((root / "uniform/completed" / slug).glob("q*.json"))
        actual = {path.stem for path in files}
        if actual != expected:
            raise RuntimeError(f"{slug}: missing={sorted(expected-actual)} extra={sorted(actual-expected)}")
        cells[slug] = {}
        for path in files:
            record = json.loads(path.read_text())
            trace = root / record["trace_file"]
            if sha(trace) != record["runner"]["trace_sha256"]:
                raise RuntimeError(f"{slug}/{path.stem}: trace hash mismatch")
            cells[slug][path.stem] = record["runner"]["trace_sha256"]
    if list((root / "uniform/results/cells").glob("*/trials-auto-scored.jsonl")):
        raise RuntimeError("scored files exist before execution freeze")
    record = {
        "cohort": "experiment_4a_uniform_random",
        "status": "frozen_before_scoring_and_trace_analysis",
        "cells": cells,
        "trials_per_cell": 45,
        "signal_trials_per_cell": 40,
        "controls_per_cell": 5,
        "total_fresh_trials": 90,
        "prompt_freeze_sha256": sha(root / "uniform/results/prompt-freeze.json"),
        "response_text_inspected_before_freeze": False,
        "trace_content_inspected_before_freeze": False,
        "direct_api_calls": 0,
    }
    atomic_json(output, record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
