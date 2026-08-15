#!/usr/bin/env python3
"""Fail-closed validation for the five-symbol instrument cohorts."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from generate_clean import CLEAN_REPLICATES, ROOT, SCRAMBLED_CONTROLS
from hidden_tasks import PAYLOAD_A, PAYLOAD_B, SYMBOLS, validate_tasks


EXPECTED_COUNTS = {"clean": CLEAN_REPLICATES * 2, "scrambled": SCRAMBLED_CONTROLS}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(*, require_freeze: bool = False) -> dict:
    task = validate_tasks()
    prompt_hashes = {}
    cohorts = {}
    for cohort, expected_count in EXPECTED_COUNTS.items():
        root = ROOT / "cohorts" / cohort
        manifest = json.loads((root / "manifest.json").read_text())
        rows = manifest["trials"]
        if len(rows) != expected_count:
            raise RuntimeError(f"unexpected {cohort} trial count")
        ids = {row["trial_id"] for row in rows}
        if set(manifest["query_order"]) != ids or len(manifest["query_order"]) != len(ids):
            raise RuntimeError(f"invalid {cohort} query order")
        identity_counts = Counter()
        for row in rows:
            trial_id = row["trial_id"]
            metadata = json.loads((root / "metadata" / f"{trial_id}.json").read_text())
            if metadata != row:
                raise RuntimeError(f"manifest/metadata mismatch: {trial_id}")
            prompt_path = ROOT / row["prompt_file"]
            words = prompt_path.read_text().split()
            if Counter(words) != Counter(PAYLOAD_A):
                raise RuntimeError(f"word-bag mismatch: {trial_id}")
            if any(words.count(symbol) != 1 for symbol in SYMBOLS):
                raise RuntimeError(f"symbol frequency mismatch: {trial_id}")
            if sha256(prompt_path) != row["prompt_sha256"]:
                raise RuntimeError(f"prompt hash mismatch: {trial_id}")
            if cohort == "clean":
                identity = row["payload_identity"]
                expected = PAYLOAD_A if identity == "A" else PAYLOAD_B
                if words != expected:
                    raise RuntimeError(f"clean rendering mismatch: {trial_id}")
                identity_counts[identity] += 1
            else:
                if words in (PAYLOAD_A, PAYLOAD_B):
                    raise RuntimeError(f"intact scrambled control: {trial_id}")
                if [PAYLOAD_A[index] for index in row["source_indices"]] != words:
                    raise RuntimeError(f"scrambled index mismatch: {trial_id}")
            prompt_hashes[trial_id] = row["prompt_sha256"]
        if cohort == "clean" and identity_counts != {"A": 20, "B": 20}:
            raise RuntimeError("clean identity balance mismatch")
        cohorts[cohort] = {"trials": len(rows), "passed": True}
    result = {
        "passed": True,
        "task": task,
        "cohorts": cohorts,
        "prompt_hashes": prompt_hashes,
        "scheduled_prompts": len(prompt_hashes),
    }
    if require_freeze:
        freeze = json.loads((ROOT / "results/protocol-freeze.json").read_text())
        if freeze["prompt_hashes"] != prompt_hashes:
            raise RuntimeError("frozen prompt hashes changed")
        if freeze["task_validation"] != task:
            raise RuntimeError("frozen task changed")
    return result


def main() -> None:
    result = validate(require_freeze=(ROOT / "results/protocol-freeze.json").exists())
    (ROOT / "results/invariants.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
