#!/usr/bin/env python3
"""Generate, validate, and freeze only the v2 clean-validation cohort."""

from __future__ import annotations

import hashlib
import json
import platform
import random
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from hidden_tasks import ANSWERS, PAYLOAD_A, PAYLOAD_B, SYMBOLS, validate_tasks
from runtime import DISABLED_FEATURES, EFFORT, IMAGE, MODEL


ROOT = Path(__file__).resolve().parent
VERSION = "experiment-6-five-symbol-v2"
SOURCE_FILES = ("README.md", "hidden_tasks.py", "runtime.py", "prepare.py", "run_clean.py", "score_clean.py")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_int(*parts: object) -> tuple[str, int]:
    material = "\n".join(map(str, (VERSION,) + parts))
    return material, int(hashlib.sha256(material.encode()).hexdigest(), 16)


def main() -> None:
    freeze_path = ROOT / "results/protocol-freeze.json"
    if freeze_path.exists():
        raise RuntimeError("v2 protocol already frozen")
    task = validate_tasks()
    rows = []
    number = 1
    for identity, payload in (("A", PAYLOAD_A), ("B", PAYLOAD_B)):
        for replicate in range(1, 21):
            trial_id = f"q{number:04d}"
            text = " ".join(payload) + "\n"
            prompt_path = ROOT / "cohorts/clean/prompts" / f"{trial_id}.txt"
            metadata_path = ROOT / "cohorts/clean/metadata" / f"{trial_id}.json"
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            row = {
                "trial_id": trial_id,
                "cohort": "clean",
                "payload_identity": identity,
                "replicate": replicate,
                "expected_answer": " ".join(ANSWERS[identity]),
                "prompt_words": len(payload),
                "prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "prompt_file": str(prompt_path.relative_to(ROOT)),
            }
            prompt_path.write_text(text)
            metadata_path.write_text(json.dumps(row, indent=2) + "\n")
            rows.append(row)
            number += 1
    if any(Counter((ROOT / row["prompt_file"]).read_text().split()) != Counter(PAYLOAD_A) for row in rows):
        raise RuntimeError("clean word-bag mismatch")
    if any(
        (ROOT / row["prompt_file"]).read_text().split()
        != (PAYLOAD_A if row["payload_identity"] == "A" else PAYLOAD_B)
        for row in rows
    ):
        raise RuntimeError("clean rendering mismatch")
    if any(
        (ROOT / row["prompt_file"]).read_text().split().count(symbol) != 1
        for row in rows for symbol in SYMBOLS
    ):
        raise RuntimeError("candidate-symbol count mismatch")
    order_material, order_seed = seed_int("query-order", "clean")
    query_order = [row["trial_id"] for row in rows]
    random.Random(order_seed).shuffle(query_order)
    manifest = {
        "cohort": "clean",
        "trials": rows,
        "query_order": query_order,
        "query_order_seed_material": order_material,
        "query_order_seed_sha256": hashlib.sha256(order_material.encode()).hexdigest(),
    }
    (ROOT / "cohorts/clean/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    prompt_hashes = {row["trial_id"]: row["prompt_sha256"] for row in rows}
    freeze = {
        "schema_version": 1,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": "6A-five-symbol-instrument-v2-clean",
        "v1_failure_tag": "experiment-6-five-symbol-v1-clean-failed",
        "repository_commit_before_v2": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "model": MODEL,
        "reasoning": EFFORT,
        "image": IMAGE,
        "python_version": platform.python_version(),
        "task_validation": task,
        "prompt_hashes": prompt_hashes,
        "query_order": query_order,
        "clean_gate": {"A_at_least": 18, "B_at_least": 18, "trials_per_identity": 20},
        "timeout_seconds": 600,
        "workers": 3,
        "responses_freeze_before_scoring": True,
        "no_scrambled_or_interference_prompts_generated": True,
        "direct_api_used": False,
        "disabled_features": list(DISABLED_FEATURES),
        "source_hashes": {name: sha256(ROOT / name) for name in SOURCE_FILES},
    }
    freeze_path.parent.mkdir(parents=True, exist_ok=True)
    freeze_path.write_text(json.dumps(freeze, indent=2) + "\n")
    (ROOT / "results/invariants.json").write_text(json.dumps({
        "passed": True,
        "task": task,
        "clean_trials": len(rows),
        "prompt_hashes": prompt_hashes,
        "word_bags_equal_across_A_B": True,
    }, indent=2) + "\n")
    print(json.dumps({"task": task, "clean_trials": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
