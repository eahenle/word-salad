#!/usr/bin/env python3
"""Freeze the cell-level Experiment 3 confirmation plan before execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from runtime import atomic_json, cell_slug


SELECTED = (
    ("gpt-5.6-sol", "medium", "lowest-effort configuration with robust fixed and jitter recovery"),
    ("gpt-5.6-terra", "xhigh", "intermediate capability boundary with 3/10 jitter pairs"),
    ("gpt-5.3-codex-spark", "xhigh", "lower boundary with one jitter answer and zero complete pairs"),
)


def main() -> None:
    root = Path(__file__).resolve().parent
    output = root / "results" / "confirmation-plan.json"
    if output.exists():
        raise FileExistsError(f"confirmation plan already frozen: {output}")
    screening = root / "results" / "screening-freeze.json"
    analysis = root / "results" / "analysis.md"
    if not screening.exists() or not analysis.exists():
        raise RuntimeError("frozen screening cohort and analysis required")
    ids = [
        *(f"q{number:04d}" for number in range(11, 21)),
        *(f"q{number:04d}" for number in range(31, 41)),
        *(f"q{number:04d}" for number in range(51, 61)),
        *(f"q{number:04d}" for number in range(71, 81)),
    ]
    prompt_manifest = json.loads((root / "results" / "prompt-manifest.json").read_text())
    hashes = {row["neutral_id"]: row["prompt_sha256"] for row in prompt_manifest}
    if set(ids) - set(hashes):
        raise RuntimeError("confirmation IDs missing from prompt manifest")
    for model, effort, _ in SELECTED:
        slug = cell_slug(model, effort)
        already = [trial_id for trial_id in ids if (root / "completed" / slug / f"{trial_id}.json").exists()]
        if already:
            raise RuntimeError(f"{slug}: confirmation already started: {already}")
    record = {
        "status": "frozen_before_confirmation_execution",
        "selection_unit": "whole model/reasoning cells, never individual seeds",
        "selection_source": "frozen 10-pair common screening matrix",
        "selected_cells": [
            {"model": model, "reasoning": effort, "rationale": rationale}
            for model, effort, rationale in SELECTED
        ],
        "carriers": ["fixed", "jitter"],
        "payload_identities": ["A", "B"],
        "seeds": list(range(11, 21)),
        "trial_ids_per_cell": ids,
        "prompt_hashes": {trial_id: hashes[trial_id] for trial_id in ids},
        "trials_per_cell": 40,
        "total_trials": 120,
        "controls_expanded": False,
        "timeout_seconds": 900,
        "workers": 4,
        "direct_api_calls_planned": 0,
        "screening_freeze_sha256": hashlib.sha256(screening.read_bytes()).hexdigest(),
        "screening_analysis_sha256": hashlib.sha256(analysis.read_bytes()).hexdigest(),
    }
    atomic_json(output, record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
