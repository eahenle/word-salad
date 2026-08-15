#!/usr/bin/env python3
"""Fail-closed validation of every frozen balanced-density prompt candidate."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from generate import CONDITIONS, FRAME, ROOT, SEEDS, STAGES, render
from hidden_tasks import ANSWERS, PAYLOAD_A, PAYLOAD_B, SYMBOLS, validate_tasks


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(*, require_freeze: bool = False) -> dict:
    task = validate_tasks()
    stage_results = {}
    prompt_hashes = {}
    for stage, total_words in STAGES.items():
        root = ROOT / "stages" / stage
        manifest = json.loads((root / "manifest.json").read_text())
        if len(manifest["trials"]) != len(SEEDS) * len(CONDITIONS):
            raise RuntimeError(f"unexpected trial count: {stage}")
        if set(manifest["query_order"]) != {row["trial_id"] for row in manifest["trials"]}:
            raise RuntimeError(f"query order mismatch: {stage}")
        by_seed = {}
        for row in manifest["trials"]:
            trial_id = row["trial_id"]
            metadata_path = root / "metadata" / f"{trial_id}.json"
            metadata = json.loads(metadata_path.read_text())
            if metadata != row:
                raise RuntimeError(f"manifest/metadata mismatch: {trial_id}")
            document_path = root / "documents" / f"{trial_id}.txt"
            prompt_path = root / "prompts" / f"{trial_id}.txt"
            document_words = document_path.read_text().split()
            prompt_text = prompt_path.read_text()
            if len(document_words) != total_words:
                raise RuntimeError(f"document length mismatch: {trial_id}")
            if prompt_text != FRAME + "\n\n" + document_path.read_text():
                raise RuntimeError(f"framing mismatch: {trial_id}")
            positions = metadata["signal_positions"]
            if len(positions) != len(PAYLOAD_A) or len(set(positions)) != len(PAYLOAD_A):
                raise RuntimeError(f"carrier count/uniqueness mismatch: {trial_id}")
            extracted = [document_words[position] for position in positions]
            if extracted != metadata["signal_words_rendered"]:
                raise RuntimeError(f"signal extraction mismatch: {trial_id}")
            if extracted != render(metadata["signal_source_indices"]):
                raise RuntimeError(f"source-index extraction mismatch: {trial_id}")
            if metadata["condition"] == "hidden_a" and extracted != PAYLOAD_A:
                raise RuntimeError(f"A signal mismatch: {trial_id}")
            if metadata["condition"] == "hidden_b" and extracted != PAYLOAD_B:
                raise RuntimeError(f"B signal mismatch: {trial_id}")
            if metadata["condition"] == "scrambled" and extracted in (PAYLOAD_A, PAYLOAD_B):
                raise RuntimeError(f"accidentally intact scrambled control: {trial_id}")
            if any(document_words.count(symbol) != 1 for symbol in SYMBOLS):
                raise RuntimeError(f"candidate-symbol frequency mismatch: {trial_id}")
            if sha256(document_path) != metadata["document_sha256"]:
                raise RuntimeError(f"document hash mismatch: {trial_id}")
            if sha256(prompt_path) != metadata["prompt_sha256"]:
                raise RuntimeError(f"prompt hash mismatch: {trial_id}")
            prompt_hashes[trial_id] = metadata["prompt_sha256"]
            by_seed.setdefault(metadata["seed"], {})[metadata["condition"]] = document_words
        for seed, conditions in by_seed.items():
            if set(conditions) != set(CONDITIONS):
                raise RuntimeError(f"incomplete matched seed: {stage}/{seed}")
            bags = [Counter(conditions[condition]) for condition in CONDITIONS]
            if not all(bag == bags[0] for bag in bags[1:]):
                raise RuntimeError(f"matched full-document bags differ: {stage}/{seed}")
        stage_results[stage] = {
            "trials": len(manifest["trials"]),
            "matched_seeds": len(by_seed),
            "signal_words": len(PAYLOAD_A),
            "document_words": total_words,
            "actual_density": len(PAYLOAD_A) / total_words,
            "all_invariants_passed": True,
        }
    result = {
        "passed": True,
        "task": task,
        "expected_answers": {key: " ".join(value) for key, value in ANSWERS.items()},
        "stage_results": stage_results,
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
