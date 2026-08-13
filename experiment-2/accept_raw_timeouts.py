#!/usr/bin/env python3
"""Accept exact zero-byte ~600-second API disconnects as timeout outcomes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from generate import build_tasks


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent
    tasks = {task.neutral_id: task for task in build_tasks(root)}
    written = 0
    for path in sorted(
        (root / "raw-model" / "infrastructure-failures").glob("r*/attempt-*/attempt.json")
    ):
        attempt = json.loads(path.read_text())
        trial_id = attempt["neutral_id"]
        exception = attempt.get("exception") or ""
        elapsed = attempt.get("elapsed_seconds")
        if not (
            "RemoteDisconnected" in exception
            and isinstance(elapsed, (int, float))
            and 590 <= elapsed <= 660
            and attempt.get("http_status") is None
            and attempt.get("response_bytes") == 0
        ):
            continue
        task = tasks[trial_id]
        if attempt["prompt_sha256"] != task.metadata["prompt_sha256"]:
            raise RuntimeError(f"{trial_id}: prompt hash mismatch")
        record = {
            "neutral_id": trial_id,
            "outcome": "timeout_nonresponse",
            "protocol_seconds": 600,
            "observed_elapsed_seconds": elapsed,
            "prompt_sha256": attempt["prompt_sha256"],
            "source_attempt": str(path.relative_to(root)),
            "source_attempt_sha256": digest(path),
            "response_bytes": 0,
            "retry": False,
            "decision": "accepted as a scheduled data point by coordinator instruction",
        }
        output = root / "raw-model" / "timeouts" / f"{trial_id}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(record, indent=2) + "\n"
        if output.exists() and output.read_text() != rendered:
            raise RuntimeError(f"{trial_id}: existing timeout decision differs")
        output.write_text(rendered)
        written += 1
    print(f"accepted or verified {written} timeout/nonresponse outcomes")


if __name__ == "__main__":
    main()
