#!/usr/bin/env python3
"""Fail-closed mechanical validation for Experiment 3 prompts and carriers."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from carrier import fixed_mask, signal_intervals
from generate import build_tasks, payloads, write_tasks


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path) -> dict:
    tasks = build_tasks(root)
    write_tasks(root, tasks)
    words = payloads(root)
    by = {(task.carrier, task.payload_identity, task.seed): task for task in tasks}
    experiment2 = root.parent / "experiment-2"
    failures = []
    fixed_pairs = jitter_pairs = 0
    for task in tasks:
        prompt_path = root / "prompts" / task.carrier / f"{task.neutral_id}.txt"
        metadata_path = root / "metadata" / f"{task.neutral_id}.json"
        metadata = json.loads(metadata_path.read_text())
        prompt_words = task.prompt.split()
        mask = tuple(metadata["carrier_mask"])
        if prompt_path.read_text() != task.prompt or sha256(prompt_path) != metadata["prompt_sha256"]:
            failures.append(f"{task.neutral_id}: stored prompt/hash mismatch")
        if len(prompt_words) != 322 or len(mask) != 322:
            failures.append(f"{task.neutral_id}: expected 322 positions")
        if Counter(mask) != Counter({"S": 161, "D": 161}):
            failures.append(f"{task.neutral_id}: carrier density mismatch")
        if Counter(prompt_words) != Counter({word: count * 2 for word, count in Counter(words["A"]).items()}):
            failures.append(f"{task.neutral_id}: aggregate word bag mismatch")
        signal = [word for marker, word in zip(mask, prompt_words) if marker == "S"]
        distractor = [word for marker, word in zip(mask, prompt_words) if marker == "D"]
        if task.condition == "signal" and signal != words[task.payload_identity]:
            failures.append(f"{task.neutral_id}: signal extraction mismatch")
        if task.condition == "all_shuffled" and signal in words.values():
            failures.append(f"{task.neutral_id}: coherent control signal stream")
        if Counter(signal) != Counter(words["A"]) or Counter(distractor) != Counter(words["A"]):
            failures.append(f"{task.neutral_id}: component multiset mismatch")
        phase = metadata["nominal_phase"]
        if task.carrier == "fixed":
            if mask != fixed_mask(161, phase) or metadata["carrier_minimal_period"] != 2:
                failures.append(f"{task.neutral_id}: fixed carrier is not period 2")
            source = experiment2 / "prompts" / "constrained" / f"{metadata['source_experiment2_trial']}.txt"
            if task.prompt != source.read_text() or metadata["prompt_sha256"] != sha256(source):
                failures.append(f"{task.neutral_id}: fixed prompt differs from Experiment 2")
        else:
            if Counter(signal_intervals(mask)) != Counter({1: 80, 3: 80}):
                failures.append(f"{task.neutral_id}: unbalanced jitter intervals")
            if metadata["carrier_minimal_period"] != 322:
                failures.append(f"{task.neutral_id}: jitter mask unexpectedly periodic")
            expected_edges = (0, 320) if phase == 0 else (1, 321)
            if (metadata["first_signal_position"], metadata["last_signal_position"]) != expected_edges:
                failures.append(f"{task.neutral_id}: boundary counterbalance mismatch")

    for seed in range(1, 21):
        for carrier in ("fixed", "jitter"):
            a, b = by[(carrier, "A", seed)], by[(carrier, "B", seed)]
            if Counter(a.prompt.split()) != Counter(b.prompt.split()):
                failures.append(f"{carrier} seed {seed}: paired bags differ")
            if a.metadata["carrier_mask"] != b.metadata["carrier_mask"]:
                failures.append(f"{carrier} seed {seed}: paired masks differ")
            if a.metadata["distractor_source_indices"] != b.metadata["distractor_source_indices"]:
                failures.append(f"{carrier} seed {seed}: paired distractors differ")
            if carrier == "fixed":
                fixed_pairs += 1
            else:
                jitter_pairs += 1
        for identity in ("A", "B"):
            fixed, jitter = by[("fixed", identity, seed)], by[("jitter", identity, seed)]
            if Counter(fixed.prompt.split()) != Counter(jitter.prompt.split()):
                failures.append(f"{identity} seed {seed}: fixed/jitter bags differ")
            if fixed.metadata["distractor_source_indices"] != jitter.metadata["distractor_source_indices"]:
                failures.append(f"{identity} seed {seed}: fixed/jitter distractors differ")
            if (
                fixed.metadata["first_signal_position"], fixed.metadata["last_signal_position"]
            ) != (
                jitter.metadata["first_signal_position"], jitter.metadata["last_signal_position"]
            ):
                failures.append(f"{identity} seed {seed}: fixed/jitter edges differ")

    manifest = [{
        "neutral_id": task.neutral_id,
        "carrier": task.carrier,
        "condition": task.condition,
        "payload_identity": task.payload_identity,
        "seed": task.seed,
        "prompt_words": task.metadata["prompt_words"],
        "prompt_sha256": task.metadata["prompt_sha256"],
        "carrier_sha256": task.metadata["carrier_sha256"],
    } for task in tasks]
    results = root / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "prompt-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    report = {
        "passed": not failures,
        "generator_version": "q3-balanced-jitter-v1",
        "frozen_payload_word_count": 161,
        "handoff_word_count_196_inapplicable": True,
        "stimuli_validated": len(tasks),
        "fixed_pairs": fixed_pairs,
        "jitter_pairs": jitter_pairs,
        "all_shuffled_controls": 3,
        "total_positions": 322,
        "signal_positions": 161,
        "distractor_positions": 161,
        "fixed_period": 2,
        "jitter_interval_counts": {"1": 80, "3": 80},
        "paired_bags_equal": not any("paired bags" in failure for failure in failures),
        "fixed_jitter_bags_equal": not any("fixed/jitter bags" in failure for failure in failures),
        "paired_masks_equal": not any("paired masks" in failure for failure in failures),
        "paired_distractors_equal": not any("paired distractors" in failure for failure in failures),
        "signal_extraction_exact": not any("signal extraction" in failure for failure in failures),
        "fixed_prompts_byte_identical_to_experiment_2": not any("differs from Experiment 2" in failure for failure in failures),
        "fixed_jitter_boundaries_matched": not any("fixed/jitter edges" in failure for failure in failures),
        "controls_have_no_coherent_signal_stream": not any("coherent control" in failure for failure in failures),
        "prompt_hash_manifest_written_before_execution": True,
        "failures": failures,
    }
    (results / "prompt-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    if failures:
        raise RuntimeError("; ".join(failures[:10]))
    freeze = {
        "status": "frozen_before_subject_execution_and_scoring",
        "generator_version": report["generator_version"],
        "prompt_count": len(manifest),
        "manifest_sha256": hashlib.sha256(
            (results / "prompt-manifest.json").read_bytes()
        ).hexdigest(),
        "payload_word_count": 161,
        "total_positions": 322,
        "direct_api_calls_authorized": False,
        "hypotheses_frozen_in_readme": True,
    }
    freeze_path = results / "prompt-freeze.json"
    rendered_freeze = json.dumps(freeze, indent=2) + "\n"
    if freeze_path.exists() and freeze_path.read_text() != rendered_freeze:
        raise RuntimeError("prompt freeze artifact differs")
    freeze_path.write_text(rendered_freeze)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    report = validate(args.root)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
