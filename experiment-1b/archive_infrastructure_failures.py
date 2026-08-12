#!/usr/bin/env python3
"""Archive mechanically identified infrastructure failures before selective retries.

Timeouts are subject outcomes and are never eligible. The script is deliberately
separate from the runner so a retry cannot occur implicitly or overwrite evidence.
"""

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

ELIGIBLE_ERROR_TYPES = {
    "runner_exception",
    "nonzero_exit",
    "missing_final_agent_message",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def eligible_records(root: Path) -> list[dict]:
    records = []
    for path in sorted((root / "completed").glob("q*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        error = record.get("runner", {}).get("error") or {}
        if error.get("type") in ELIGIBLE_ERROR_TYPES:
            records.append(record)
    return records


def next_attempt_directory(root: Path, neutral_id: str) -> Path:
    parent = root / "invalidated-attempts" / neutral_id
    indices = []
    if parent.exists():
        for path in parent.glob("attempt-*"):
            try:
                indices.append(int(path.name.removeprefix("attempt-")))
            except ValueError:
                pass
    return parent / f"attempt-{max(indices, default=0) + 1}"


def archive(root: Path, record: dict) -> Path:
    neutral_id = record["neutral_id"]
    destination = next_attempt_directory(root, neutral_id)
    destination.mkdir(parents=True, exist_ok=False)
    sources: dict[str, Path] = {}
    for archived_name, (directory, suffix) in ARTIFACTS.items():
        source = root / directory / f"{neutral_id}{suffix}"
        if not source.is_file():
            raise FileNotFoundError(source)
        sources[archived_name] = source
    decision = {
        "neutral_id": neutral_id,
        "decision": "retry_with_fresh_subject",
        "decision_basis": "mechanically eligible controller_or_transport_failure",
        "archived_at": utc_now(),
        "runner_error": record["runner"]["error"],
        "original_artifacts": {
            name: {
                "relative_path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for name, path in sources.items()
        },
    }
    (destination / "retry-decision.json").write_text(
        json.dumps(decision, indent=2) + "\n", encoding="utf-8"
    )
    for archived_name, source in sources.items():
        shutil.move(str(source), destination / archived_name)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--trial-ids", nargs="+")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="move eligible evidence into invalidated-attempts; default is audit-only",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    records = eligible_records(root)
    if args.trial_ids:
        requested = set(args.trial_ids)
        available = {record["neutral_id"] for record in records}
        unknown = requested - available
        if unknown:
            raise ValueError(f"not eligible infrastructure failures: {sorted(unknown)}")
        records = [record for record in records if record["neutral_id"] in requested]
    print("eligible infrastructure failures:", " ".join(r["neutral_id"] for r in records) or "none")
    if not args.apply:
        return
    for record in records:
        destination = archive(root, record)
        print(f"archived {record['neutral_id']} -> {destination.relative_to(root)}")


if __name__ == "__main__":
    main()
