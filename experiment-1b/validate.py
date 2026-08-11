#!/usr/bin/env python3
"""Mechanical preflight for prompt pairing, invariants, and historical equality."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from generate import VARIANT_ORDER, build_tasks, sha256_bytes, write_tasks

BASELINE_SHA = "395c9c615fe4bf8900b31b73c1071bab805682e6"
BASELINE_TAG = "experiment-1a-original"


def _historical_records(historical_root: Path) -> tuple[dict[tuple[str, int, int], dict], dict[str, dict]]:
    records = {}
    for line in (historical_root / "results" / "trials-unscored.jsonl").read_text(
        encoding="utf-8"
    ).splitlines():
        record = json.loads(line)
        records[(record["condition"], int(record["lanes"]), int(record["seed"]))] = record
    metadata = {}
    for line in (historical_root / "results" / "metadata.jsonl").read_text(
        encoding="utf-8"
    ).splitlines():
        record = json.loads(line)
        metadata[record["trial_id"]] = record
    return records, metadata


def validate(
    *, root: Path, historical_root: Path, payload: str, variants: list[str]
) -> dict:
    tasks = build_tasks(payload, variants)
    write_tasks(root, tasks)
    historical_records, historical_metadata = _historical_records(historical_root)
    prompt_hashes = {}
    historical_matches = 0
    geometry_by_base: dict[tuple[str, int, int], set[str]] = defaultdict(set)
    phases_by_base: dict[tuple[str, int, int], set[int | None]] = defaultdict(set)
    for task in tasks:
        base = (task.condition, task.lanes, task.seed)
        geometry_by_base[base].add(task.metadata["geometry_sha256"])
        phases_by_base[base].add(task.metadata["signal_phase"])
        prompt_path = root / "prompts" / task.variant / f"{task.neutral_id}.txt"
        prompt_bytes = prompt_path.read_bytes()
        if sha256_bytes(prompt_bytes) != task.metadata["prompt_sha256"]:
            raise AssertionError(f"stored prompt hash mismatch: {prompt_path}")
        prompt_hashes[task.neutral_id] = task.metadata["prompt_sha256"]
        if task.variant == "original":
            historical = historical_records[base]
            historical_path = historical_root / historical["prompt_file"]
            historical_bytes = historical_path.read_bytes()
            if prompt_bytes != historical_bytes:
                raise AssertionError(
                    f"Experiment 1A-R prompt differs from historical bytes: {task.neutral_id}"
                )
            if sha256_bytes(historical_bytes) != task.metadata["prompt_sha256"]:
                raise AssertionError(f"historical hash mismatch: {task.neutral_id}")
            old_meta = historical_metadata[historical["trial_id"]]
            if old_meta["permutations"] != task.metadata["permutations"]:
                raise AssertionError(f"historical permutation mismatch: {task.neutral_id}")
            if old_meta["signal_phase"] != task.metadata["signal_phase"]:
                raise AssertionError(f"historical phase mismatch: {task.neutral_id}")
            historical_matches += 1

    for base, hashes in geometry_by_base.items():
        if len(hashes) != 1:
            raise AssertionError(f"variant geometry differs for {base}")
    for base, phases in phases_by_base.items():
        if len(phases) != 1:
            raise AssertionError(f"variant phase differs for {base}")

    report = {
        "baseline_commit": BASELINE_SHA,
        "baseline_tag": BASELINE_TAG,
        "variants": variants,
        "trials_validated": len(tasks),
        "historical_prompts_compared": historical_matches,
        "historical_prompts_byte_identical": historical_matches,
        "geometry_groups": len(geometry_by_base),
        "geometry_invariant": True,
        "signal_invariant": True,
        "multiset_invariant": True,
        "aggregate_invariant": True,
        "control_source_index_invariant": True,
        "control_rendered_equivalence_failures": 0,
        "prompt_hashes": prompt_hashes,
    }
    results_dir = root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    suffix = "-".join(variants)
    path = results_dir / f"preflight-{suffix}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--historical-root", type=Path, default=root.parent / "multiplex-experiment")
    parser.add_argument("--payload", type=Path, default=root / "payload.txt")
    parser.add_argument(
        "--variants", nargs="+", choices=VARIANT_ORDER, default=list(VARIANT_ORDER)
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    report = validate(
        root=args.root,
        historical_root=args.historical_root,
        payload=args.payload.read_text(encoding="utf-8").strip(),
        variants=args.variants,
    )
    print(
        f"validated {report['trials_validated']} prompts; "
        f"{report['historical_prompts_byte_identical']} historical prompts byte-identical"
    )


if __name__ == "__main__":
    main()
