#!/usr/bin/env python3
"""Materialize exact Experiment 2 Sol-xhigh fixed reference records read-only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from generate import build_tasks


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = args.root
    tasks = {task.neutral_id: task for task in build_tasks(root) if task.carrier == "fixed"}
    source_root = root.parent / "experiment-2"
    source_records = {record["neutral_id"]: record for record in read_jsonl(source_root / "results" / "trials.jsonl")}
    source_metrics = {record["neutral_id"]: record for record in read_jsonl(source_root / "results" / "trace-metrics.jsonl")}
    records = []
    mapping = []
    for task in tasks.values():
        source_id = task.metadata["source_experiment2_trial"]
        source = source_records[source_id]
        metric = source_metrics[source_id]
        if source["prompt_sha256"] != task.metadata["prompt_sha256"]:
            raise RuntimeError(f"{task.neutral_id}: source prompt hash mismatch")
        record = dict(source)
        record.update({
            "trial_id": task.neutral_id,
            "neutral_id": task.neutral_id,
            "carrier": "fixed",
            "condition": "signal",
            "payload_identity": task.payload_identity,
            "answer_identity": task.answer_identity,
            "seed": task.seed,
            "prompt_file": f"prompts/fixed/{task.neutral_id}.txt",
            "execution_origin": "reused_frozen_experiment_2",
            "source_experiment": "experiment-2",
            "source_trial_id": source_id,
            "source_trace_file": source["trace_file"],
            "source_stderr_file": source["stderr_file"],
        })
        record.pop("trace_file", None)
        record.pop("stderr_file", None)
        records.append(record)
        mapping.append({
            "experiment_3_trial": task.neutral_id,
            "experiment_2_trial": source_id,
            "prompt_sha256": task.metadata["prompt_sha256"],
            "trace_sha256": source["runner"]["trace_sha256"],
            "trace_metric_sha256": hashlib.sha256(
                json.dumps(metric, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        })
    results = root / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "reused-fixed-sol-xhigh.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    )
    (results / "reused-fixed-mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    print(f"materialized {len(records)} exact frozen Sol-xhigh fixed references")


if __name__ == "__main__":
    main()
