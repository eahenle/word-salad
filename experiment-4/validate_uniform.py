#!/usr/bin/env python3
"""Fail-closed mechanical validation and prompt freeze for Experiment 4A."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from carrier import uniform_mask
from generate_uniform import build_tasks, payloads, write_tasks


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path) -> dict:
    tasks = build_tasks(root)
    write_tasks(root, tasks)
    words = payloads(root)
    canonical_bag = Counter(words["A"])
    aggregate_bag = Counter({word: count * 2 for word, count in canonical_bag.items()})
    by = {(task.payload_identity, task.seed): task for task in tasks}
    failures: list[str] = []
    seen_masks: dict[int, str] = {}
    for task in tasks:
        prompt_path = root / "uniform/prompts" / f"{task.neutral_id}.txt"
        metadata_path = root / "uniform/metadata" / f"{task.neutral_id}.json"
        metadata = json.loads(metadata_path.read_text())
        prompt_words = task.prompt.split()
        mask = tuple(metadata["carrier_mask"])
        signal_positions = metadata["signal_positions"]
        signal = [word for marker, word in zip(mask, prompt_words) if marker == "S"]
        distractor = [word for marker, word in zip(mask, prompt_words) if marker == "D"]
        if prompt_path.read_text() != task.prompt or sha(prompt_path) != metadata["prompt_sha256"]:
            failures.append(f"{task.neutral_id}: stored prompt/hash mismatch")
        if len(prompt_words) != 322 or len(mask) != 322:
            failures.append(f"{task.neutral_id}: expected 322 positions")
        if Counter(mask) != Counter({"S": 161, "D": 161}):
            failures.append(f"{task.neutral_id}: carrier density mismatch")
        if len(signal_positions) != 161 or len(set(signal_positions)) != 161 or signal_positions != sorted(signal_positions):
            failures.append(f"{task.neutral_id}: sampled position uniqueness/order mismatch")
        if list(uniform_mask(161, task.seed)) != list(mask):
            failures.append(f"{task.neutral_id}: deterministic uniform mask mismatch")
        previous = seen_masks.setdefault(task.seed, metadata["carrier_mask"])
        if previous != metadata["carrier_mask"]:
            failures.append(f"{task.neutral_id}: seed mask differs across paired/control renderings")
        if Counter(prompt_words) != aggregate_bag:
            failures.append(f"{task.neutral_id}: aggregate bag mismatch")
        if Counter(signal) != canonical_bag or Counter(distractor) != canonical_bag:
            failures.append(f"{task.neutral_id}: stream bag mismatch")
        if task.condition == "signal" and signal != words[task.payload_identity]:
            failures.append(f"{task.neutral_id}: signal extraction mismatch")
        if task.condition == "all_shuffled" and signal in words.values():
            failures.append(f"{task.neutral_id}: control signal accidentally coherent")
        if metadata["mask_rejection_performed"]:
            failures.append(f"{task.neutral_id}: mask rejection flag set")
        for carrier, number in (("fixed", task.seed if task.payload_identity != "B" else 20 + task.seed),
                                ("jitter", 40 + task.seed if task.payload_identity != "B" else 60 + task.seed)):
            prior = root.parent / "experiment-3/prompts" / carrier / f"q{number:04d}.txt"
            if Counter(prompt_words) != Counter(prior.read_text().split()):
                failures.append(f"{task.neutral_id}: bag differs from matched Experiment 3 {carrier}")

    for seed in range(1, 21):
        a, b = by[("A", seed)], by[("B", seed)]
        if Counter(a.prompt.split()) != Counter(b.prompt.split()):
            failures.append(f"seed {seed}: paired A/B bags differ")
        if a.metadata["carrier_mask"] != b.metadata["carrier_mask"]:
            failures.append(f"seed {seed}: paired masks differ")
        if a.metadata["distractor_source_indices"] != b.metadata["distractor_source_indices"]:
            failures.append(f"seed {seed}: paired distractors differ")

    manifest = [{
        "neutral_id": task.neutral_id,
        "condition": task.condition,
        "payload_identity": task.payload_identity,
        "seed": task.seed,
        "prompt_words": task.metadata["prompt_words"],
        "prompt_sha256": task.metadata["prompt_sha256"],
        "carrier_sha256": task.metadata["carrier_sha256"],
    } for task in tasks]
    results = root / "uniform/results"
    results.mkdir(parents=True, exist_ok=True)
    manifest_path = results / "prompt-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    report = {
        "passed": not failures,
        "generator_version": "q4-uniform-random-v1",
        "stimuli_validated": len(tasks),
        "signal_prompts": 40,
        "all_shuffled_controls": 5,
        "frozen_payload_word_count": 161,
        "handoff_word_count_196_inapplicable": True,
        "total_positions": 322,
        "signal_positions": 161,
        "distractor_positions": 161,
        "uniform_sample_without_replacement": True,
        "mask_rejection_performed": False,
        "paired_bags_equal": not any("paired A/B bags" in value for value in failures),
        "paired_masks_equal": not any("paired masks" in value for value in failures),
        "paired_distractors_equal": not any("paired distractors" in value for value in failures),
        "matched_prior_carrier_bags_equal": not any("bag differs from matched" in value for value in failures),
        "signal_extraction_exact": not any("signal extraction" in value for value in failures),
        "controls_have_no_coherent_stream": not any("accidentally coherent" in value for value in failures),
        "failures": failures,
    }
    (results / "prompt-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    if failures:
        raise RuntimeError("; ".join(failures[:10]))
    freeze = {
        "status": "frozen_before_subject_execution_and_scoring",
        "generator_version": report["generator_version"],
        "prompt_count": len(manifest),
        "manifest_sha256": sha(manifest_path),
        "payload_word_count": 161,
        "total_positions": 322,
        "scheduled_models": [
            {"model": "gpt-5.6-sol", "reasoning": "medium"},
            {"model": "gpt-5.6-terra", "reasoning": "xhigh"},
        ],
        "scheduled_pairs_per_model": 20,
        "controls_per_model": 5,
        "common_minimum_stop_pairs": 10,
        "direct_api_calls_authorized": False,
        "hypotheses_and_stopping_rule_frozen_in_readme": True,
    }
    freeze_path = results / "prompt-freeze.json"
    rendered = json.dumps(freeze, indent=2) + "\n"
    if freeze_path.exists() and freeze_path.read_text() != rendered:
        raise RuntimeError("prompt freeze differs")
    freeze_path.write_text(rendered)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(validate(args.root), indent=2))


if __name__ == "__main__":
    main()
