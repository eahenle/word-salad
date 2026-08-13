#!/usr/bin/env python3
"""Archive exact usage-cap failures without treating them as subject outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS = {
    "attempt.json": ("attempts", ".json"),
    "completed.json": ("completed", ".json"),
    "trace.jsonl": ("traces", ".jsonl"),
    "stderr.txt": ("stderr", ".txt"),
}
MARKER = "you've hit your usage limit"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def eligible(root: Path) -> list[dict]:
    records = []
    for path in sorted((root / "completed").glob("r*.json")):
        record = json.loads(path.read_text())
        error = record.get("runner", {}).get("error") or {}
        if error.get("type") != "nonzero_exit":
            continue
        trace = root / record["trace_file"]
        if MARKER in trace.read_text(encoding="utf-8").lower():
            records.append(record)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--trial-ids", nargs="+")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    records = eligible(root)
    if args.trial_ids:
        requested = set(args.trial_ids)
        available = {record["neutral_id"] for record in records}
        if requested - available:
            raise ValueError(f"not exact quota failures: {sorted(requested - available)}")
        records = [record for record in records if record["neutral_id"] in requested]
    print("eligible quota failures:", " ".join(record["neutral_id"] for record in records) or "none")
    if not args.apply:
        return
    archived = []
    for record in records:
        neutral_id = record["neutral_id"]
        destination = root / "invalidated-attempts" / neutral_id / "attempt-1"
        destination.mkdir(parents=True, exist_ok=False)
        sources = {
            name: root / directory / f"{neutral_id}{suffix}"
            for name, (directory, suffix) in ARTIFACTS.items()
        }
        decision = {
            "neutral_id": neutral_id,
            "decision": "retry_exact_stimulus_after_capacity_returns",
            "decision_basis": "observable service usage-cap rejection before subject response",
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "prompt_sha256": record["prompt_sha256"],
            "original_artifacts": {
                name: {"relative_path": str(path.relative_to(root)), "bytes": path.stat().st_size,
                       "sha256": sha256(path)}
                for name, path in sources.items()
            },
        }
        (destination / "retry-decision.json").write_text(json.dumps(decision, indent=2) + "\n")
        for name, source in sources.items():
            shutil.move(str(source), destination / name)
        archived.append({
            "neutral_id": neutral_id, "prompt_sha256": record["prompt_sha256"],
            "archive": str(destination.relative_to(root)),
        })
    result = root / "results" / "pending-quota-reruns.json"
    result.write_text(json.dumps({
        "reason": "GPT-5.6-Sol usage cap reached during full slate",
        "retry_not_before_reported_by_runtime": "2026-08-19T07:10:00-07:00",
        "trial_count": len(archived), "trials": archived,
    }, indent=2) + "\n")
    print(f"archived {len(archived)} quota failures; wrote {result.relative_to(root)}")


if __name__ == "__main__":
    main()
