#!/usr/bin/env python3
"""Generate and freeze ten N=1 scrambled controls after the clean gate passes."""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
from collections import Counter
from datetime import datetime, timezone

from hidden_tasks import PAYLOAD_A, PAYLOAD_B, SYMBOLS
from runtime import EFFORT, IMAGE, MODEL, ROOT


VERSION = "experiment-6-five-symbol-v2-scrambled"
SOURCE_FILES = ("prepare_scrambled.py", "run_scrambled.py", "score_scrambled.py")


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_int(*parts: object) -> tuple[str, int]:
    material = "\n".join(map(str, (VERSION,) + parts))
    return material, int(hashlib.sha256(material.encode()).hexdigest(), 16)


def main() -> None:
    clean_gate = json.loads((ROOT / "results/clean-gate.json").read_text())
    if not clean_gate.get("advance_scrambled_authorized"):
        raise RuntimeError("clean gate does not authorize controls")
    output = ROOT / "results/scrambled-protocol-freeze.json"
    if output.exists():
        raise RuntimeError("scrambled protocol already frozen")
    rows = []
    for replicate in range(1, 11):
        trial_id = f"q{40 + replicate:04d}"
        material, value = seed_int("shuffle", replicate)
        indices = list(range(len(PAYLOAD_A)))
        rng = random.Random(value)
        while True:
            rng.shuffle(indices)
            words = [PAYLOAD_A[index] for index in indices]
            if words not in (PAYLOAD_A, PAYLOAD_B):
                break
        text = " ".join(words) + "\n"
        prompt = ROOT / "cohorts/scrambled/prompts" / f"{trial_id}.txt"
        metadata = ROOT / "cohorts/scrambled/metadata" / f"{trial_id}.json"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        metadata.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "trial_id": trial_id,
            "cohort": "scrambled",
            "replicate": replicate,
            "payload_identity": None,
            "expected_answer": None,
            "source_indices": indices,
            "shuffle_seed_material": material,
            "shuffle_seed_sha256": hashlib.sha256(material.encode()).hexdigest(),
            "prompt_words": len(words),
            "prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "prompt_file": str(prompt.relative_to(ROOT)),
        }
        prompt.write_text(text)
        metadata.write_text(json.dumps(row, indent=2) + "\n")
        rows.append(row)
    for row in rows:
        words = (ROOT / row["prompt_file"]).read_text().split()
        if Counter(words) != Counter(PAYLOAD_A):
            raise RuntimeError(f"control word-bag mismatch: {row['trial_id']}")
        if [PAYLOAD_A[index] for index in row["source_indices"]] != words:
            raise RuntimeError(f"control source-index mismatch: {row['trial_id']}")
        if any(words.count(symbol) != 1 for symbol in SYMBOLS):
            raise RuntimeError(f"control symbol frequency mismatch: {row['trial_id']}")
    order_material, order_seed = seed_int("query-order")
    query_order = [row["trial_id"] for row in rows]
    random.Random(order_seed).shuffle(query_order)
    manifest = {
        "cohort": "scrambled",
        "trials": rows,
        "query_order": query_order,
        "query_order_seed_material": order_material,
        "query_order_seed_sha256": hashlib.sha256(order_material.encode()).hexdigest(),
    }
    (ROOT / "cohorts/scrambled/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    freeze = {
        "schema_version": 1,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": "6A-five-symbol-instrument-v2-scrambled",
        "clean_validated_tag": "experiment-6-five-symbol-v2-clean-validated",
        "repository_commit_before_controls": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "model": MODEL,
        "reasoning": EFFORT,
        "image": IMAGE,
        "scheduled": 10,
        "target_sequences_allowed": 0,
        "prompt_hashes": {row["trial_id"]: row["prompt_sha256"] for row in rows},
        "query_order": query_order,
        "source_hashes": {name: sha256(ROOT / name) for name in SOURCE_FILES},
        "responses_freeze_before_scoring": True,
        "direct_api_used": False,
    }
    output.write_text(json.dumps(freeze, indent=2) + "\n")
    print(json.dumps({"scheduled": 10, "all_invariants_passed": True}, indent=2))


if __name__ == "__main__":
    main()
