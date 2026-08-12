#!/usr/bin/env python3
"""Verify the sealed Experiment 1B archive without changing trial records."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def audit(root: Path) -> dict:
    results = root / "results"
    records = read_jsonl(results / "trials-unscored.jsonl")
    expected_ids = {f"q{index:04d}" for index in range(1, 321)}
    ids = [record["neutral_id"] for record in records]
    if len(records) != 320 or set(ids) != expected_ids or len(set(ids)) != len(ids):
        raise AssertionError("unscored record cardinality or neutral-ID coverage mismatch")

    error_types: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    total_trace_bytes = 0
    total_stderr_bytes = 0
    for record in records:
        trial_id = record["neutral_id"]
        prompt = (root / record["prompt_file"]).read_bytes()
        if sha256(prompt) != record["prompt_sha256"]:
            raise AssertionError(f"prompt hash mismatch: {trial_id}")

        runner = record["runner"]
        trace = (root / record["trace_file"]).read_bytes()
        stderr = (root / record["stderr_file"]).read_bytes()
        if len(trace) != runner["trace_bytes"] or sha256(trace) != runner["trace_sha256"]:
            raise AssertionError(f"trace integrity mismatch: {trial_id}")
        if len(stderr) != runner["stderr_bytes"] or sha256(stderr) != runner["stderr_sha256"]:
            raise AssertionError(f"stderr integrity mismatch: {trial_id}")
        total_trace_bytes += len(trace)
        total_stderr_bytes += len(stderr)

        event_counts: Counter[str] = Counter()
        item_counts: Counter[str] = Counter()
        non_json = 0
        for raw_line in trace.splitlines():
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                non_json += 1
                continue
            event_counts[event.get("type", "unknown")] += 1
            item = event.get("item")
            if (
                event.get("type") == "item.completed"
                and isinstance(item, dict)
                and item.get("type")
            ):
                item_counts[item["type"]] += 1
        if sum(event_counts.values()) != runner["event_count"]:
            raise AssertionError(f"event count mismatch: {trial_id}")
        if dict(event_counts) != runner["event_type_counts"]:
            raise AssertionError(f"event type counts mismatch: {trial_id}")
        if dict(item_counts) != runner["item_type_counts"]:
            raise AssertionError(f"item type counts mismatch: {trial_id}")
        if non_json != runner["non_json_line_count"]:
            raise AssertionError(f"non-JSON count mismatch: {trial_id}")

        completion = json.loads((root / "completed" / f"{trial_id}.json").read_text())
        if completion != record:
            raise AssertionError(f"completion record differs from aggregate: {trial_id}")
        attempt = json.loads((root / "attempts" / f"{trial_id}.json").read_text())
        if attempt["prompt_sha256"] != record["prompt_sha256"]:
            raise AssertionError(f"attempt prompt hash mismatch: {trial_id}")

        error = runner.get("error")
        if error:
            error_types[error["type"]] += 1
            status_counts["error"] += 1
        else:
            status_counts["ok"] += 1

    metadata = read_jsonl(results / "metadata.jsonl")
    if len(metadata) != 320 or {item["neutral_id"] for item in metadata} != expected_ids:
        raise AssertionError("aggregate metadata coverage mismatch")

    for directory in ("attempts", "completed", "traces", "stderr"):
        if len(list((root / directory).iterdir())) != 320:
            raise AssertionError(f"unexpected file count in {directory}")

    return {
        "records": len(records),
        "neutral_ids_complete": True,
        "prompt_hashes_valid": True,
        "trace_hashes_valid": True,
        "stderr_hashes_valid": True,
        "event_counts_valid": True,
        "completion_records_match": True,
        "attempt_prompt_hashes_valid": True,
        "metadata_coverage_valid": True,
        "artifact_counts_valid": True,
        "status_counts": dict(sorted(status_counts.items())),
        "error_types": dict(sorted(error_types.items())),
        "total_trace_bytes": total_trace_bytes,
        "total_stderr_bytes": total_stderr_bytes,
    }


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument(
        "--output", type=Path, default=root / "results" / "integrity-audit.json"
    )
    args = parser.parse_args()
    report = audit(args.root)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"integrity passed: records={report['records']} "
        f"ok={report['status_counts'].get('ok', 0)} "
        f"errors={report['status_counts'].get('error', 0)}"
    )


if __name__ == "__main__":
    main()
