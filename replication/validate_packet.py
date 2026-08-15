#!/usr/bin/env python3
"""Read-only integrity validation for the external replication packet."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    execution = json.loads((ROOT / "execution-manifest.json").read_text())["trials"]
    provenance = json.loads((ROOT / "provenance-manifest.json").read_text())["trials"]
    key = json.loads((ROOT / "scoring-key.json").read_text())["trials"]
    freeze = json.loads((ROOT / "packet-freeze.json").read_text())
    if not len(execution) == len(provenance) == len(key) == 55:
        raise SystemExit("manifest lengths differ or are not 55")
    ids = [[row["trial_id"] for row in rows] for rows in (execution, provenance, key)]
    if not ids[0] == ids[1] == ids[2] or len(set(ids[0])) != 55:
        raise SystemExit("trial ID alignment failed")
    forbidden = {"study", "condition", "identity", "seed", "source", "expected_answer", "answer_A", "answer_B"}
    for row in execution:
        if forbidden.intersection(row):
            raise SystemExit(f"execution manifest leaks scoring metadata: {row['trial_id']}")
        prompt = ROOT / row["prompt_file"]
        if digest(prompt) != row["prompt_sha256"]:
            raise SystemExit(f"prompt hash mismatch: {row['trial_id']}")
        if len(prompt.read_text().split()) != row["prompt_words"]:
            raise SystemExit(f"prompt word count mismatch: {row['trial_id']}")
    for run, source in zip(execution, provenance):
        if (ROOT / run["prompt_file"]).read_bytes() != (REPO / source["source"]).read_bytes():
            raise SystemExit(f"source-byte mismatch: {run['trial_id']}")
        if run["prompt_sha256"] != source["source_sha256"]:
            raise SystemExit(f"source-hash mismatch: {run['trial_id']}")
    counts = Counter((row["study"], row["condition"], row["identity"]) for row in key)
    expected_counts = Counter({
        ("experiment-2", "signal", "A"): 10,
        ("experiment-2", "signal", "B"): 10,
        ("experiment-2", "all_shuffled", None): 10,
        ("experiment-4a", "signal", "A"): 10,
        ("experiment-4a", "signal", "B"): 10,
        ("experiment-4a", "all_shuffled", None): 5,
    })
    if counts != expected_counts:
        raise SystemExit(f"cohort counts mismatch: {counts}")
    aggregate = hashlib.sha256()
    for row in execution:
        aggregate.update(row["trial_id"].encode()); aggregate.update(b"\0")
        aggregate.update(row["prompt_sha256"].encode()); aggregate.update(b"\n")
    if aggregate.hexdigest() != freeze["prompt_set_sha256"]:
        raise SystemExit("aggregate prompt-set hash mismatch")
    print(json.dumps({"status": "pass", "trials": 55, "prompt_set_sha256": aggregate.hexdigest(), "execution_manifest_blind": True, "source_bytes_equal": True}, indent=2))


if __name__ == "__main__":
    main()
