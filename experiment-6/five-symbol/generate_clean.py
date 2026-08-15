#!/usr/bin/env python3
"""Generate clean execution and N=1 scrambled-control cohorts."""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from hidden_tasks import ANSWERS, PAYLOAD_A, PAYLOAD_B, validate_tasks


ROOT = Path(__file__).resolve().parent
VERSION = "experiment-6-five-symbol-v1"
CLEAN_REPLICATES = 20
SCRAMBLED_CONTROLS = 10


def seed_int(*parts: object) -> tuple[str, int]:
    material = "\n".join(map(str, (VERSION,) + parts))
    return material, int(hashlib.sha256(material.encode()).hexdigest(), 16)


def write_trial(cohort: str, trial_id: str, prompt_words: list[str], metadata: dict) -> dict:
    root = ROOT / "cohorts" / cohort
    text = " ".join(prompt_words) + "\n"
    prompt_path = root / "prompts" / f"{trial_id}.txt"
    metadata_path = root / "metadata" / f"{trial_id}.json"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        **metadata,
        "trial_id": trial_id,
        "cohort": cohort,
        "prompt_words": len(prompt_words),
        "prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "prompt_file": str(prompt_path.relative_to(ROOT)),
    }
    prompt_path.write_text(text)
    metadata_path.write_text(json.dumps(record, indent=2) + "\n")
    return record


def clean_trials() -> list[dict]:
    rows = []
    number = 1
    for identity, payload in (("A", PAYLOAD_A), ("B", PAYLOAD_B)):
        for replicate in range(1, CLEAN_REPLICATES + 1):
            rows.append(write_trial("clean", f"q{number:04d}", payload, {
                "condition": "clean",
                "payload_identity": identity,
                "replicate": replicate,
                "expected_answer": " ".join(ANSWERS[identity]),
            }))
            number += 1
    return rows


def scrambled_trials() -> list[dict]:
    rows = []
    for replicate in range(1, SCRAMBLED_CONTROLS + 1):
        material, value = seed_int("scrambled", replicate)
        indices = list(range(len(PAYLOAD_A)))
        rng = random.Random(value)
        while True:
            rng.shuffle(indices)
            rendered = [PAYLOAD_A[index] for index in indices]
            if rendered not in (PAYLOAD_A, PAYLOAD_B):
                break
        rows.append(write_trial("scrambled", f"q{40 + replicate:04d}", rendered, {
            "condition": "scrambled",
            "payload_identity": None,
            "replicate": replicate,
            "expected_answer": None,
            "source_indices": indices,
            "shuffle_seed_material": material,
            "shuffle_seed_sha256": hashlib.sha256(material.encode()).hexdigest(),
        }))
    return rows


def write_manifest(cohort: str, rows: list[dict]) -> None:
    material, value = seed_int("query-order", cohort)
    query_order = [row["trial_id"] for row in rows]
    random.Random(value).shuffle(query_order)
    manifest = {
        "cohort": cohort,
        "trials": rows,
        "query_order": query_order,
        "query_order_seed_material": material,
        "query_order_seed_sha256": hashlib.sha256(material.encode()).hexdigest(),
    }
    (ROOT / "cohorts" / cohort / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )


def main() -> None:
    if (ROOT / "results/protocol-freeze.json").exists():
        raise RuntimeError("protocol is frozen; prompts may not be regenerated")
    validation = validate_tasks()
    clean = clean_trials()
    scrambled = scrambled_trials()
    write_manifest("clean", clean)
    write_manifest("scrambled", scrambled)
    if any(Counter(PAYLOAD_A) != Counter(
        (ROOT / row["prompt_file"]).read_text().split()
    ) for row in clean + scrambled):
        raise RuntimeError("generated prompt word bag mismatch")
    (ROOT / "results").mkdir(parents=True, exist_ok=True)
    (ROOT / "results/generation-summary.json").write_text(json.dumps({
        "version": VERSION,
        "task": validation,
        "clean_trials": len(clean),
        "scrambled_controls": len(scrambled),
        "all_prompts_generated_before_inference": True,
    }, indent=2) + "\n")
    print(json.dumps({"clean": len(clean), "scrambled": len(scrambled)}, indent=2))


if __name__ == "__main__":
    main()
