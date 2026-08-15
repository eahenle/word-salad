#!/usr/bin/env python3
"""Build the deterministic core external-replication prompt packet."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
PROMPTS = ROOT / "frozen-prompts"
VERSION = "word-salad-external-core-v1"
ANSWER_A = "brass key = green; silver coin = blue; glass marble = green"
ANSWER_B = "brass key = green; silver coin = red; glass marble = green"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def selected_sources() -> list[dict]:
    rows = []
    # Experiment 2 constrained-output N=2: first ten seed pairs and controls.
    for seed in range(1, 11):
        rows.append({"logical_id": f"e2_s{seed:02d}_a", "study": "experiment-2", "condition": "signal", "identity": "A", "seed": seed, "source_id": f"r{40 + seed:04d}", "source": f"experiment-2/prompts/constrained/r{40 + seed:04d}.txt"})
        rows.append({"logical_id": f"e2_s{seed:02d}_b", "study": "experiment-2", "condition": "signal", "identity": "B", "seed": seed, "source_id": f"r{60 + seed:04d}", "source": f"experiment-2/prompts/constrained/r{60 + seed:04d}.txt"})
        rows.append({"logical_id": f"e2_c{seed:02d}", "study": "experiment-2", "condition": "all_shuffled", "identity": None, "seed": seed, "source_id": f"r{80 + seed:04d}", "source": f"experiment-2/prompts/constrained/r{80 + seed:04d}.txt"})
    # Experiment 4A uniform Sol-medium cohort: first ten seed pairs and all controls.
    for seed in range(1, 11):
        rows.append({"logical_id": f"e4_s{seed:02d}_a", "study": "experiment-4a", "condition": "signal", "identity": "A", "seed": seed, "source_id": f"q{seed:04d}", "source": f"experiment-4/uniform/prompts/q{seed:04d}.txt"})
        rows.append({"logical_id": f"e4_s{seed:02d}_b", "study": "experiment-4a", "condition": "signal", "identity": "B", "seed": seed, "source_id": f"q{20 + seed:04d}", "source": f"experiment-4/uniform/prompts/q{20 + seed:04d}.txt"})
    for seed in range(1, 6):
        rows.append({"logical_id": f"e4_c{seed:02d}", "study": "experiment-4a", "condition": "all_shuffled", "identity": None, "seed": seed, "source_id": f"q{40 + seed:04d}", "source": f"experiment-4/uniform/prompts/q{40 + seed:04d}.txt"})
    return rows


def main() -> None:
    rows = selected_sources()
    if len(rows) != 55:
        raise AssertionError("replication packet must contain exactly 55 prompts")
    logical_ids = {row["logical_id"] for row in rows}
    if len(logical_ids) != len(rows):
        raise AssertionError("duplicate logical IDs")
    experiment_2_metadata = {
        row["neutral_id"]: row
        for row in (
            json.loads(line)
            for line in (REPO / "experiment-2/results/metadata.jsonl").read_text().splitlines()
            if line
        )
    }
    experiment_4a_metadata = {
        row["neutral_id"]: row
        for row in json.loads(
            (REPO / "experiment-4/uniform/results/prompt-manifest.json").read_text()
        )
    }
    # Order depends only on the frozen protocol label and logical ID.
    rows.sort(key=lambda row: hashlib.sha256(f"{VERSION}|{row['logical_id']}".encode()).digest())
    PROMPTS.mkdir(parents=True, exist_ok=True)
    execution, provenance, key = [], [], []
    for index, row in enumerate(rows, start=1):
        trial_id = f"p{index:04d}"
        source = REPO / row["source"]
        data = source.read_bytes()
        destination = PROMPTS / f"{trial_id}.txt"
        if destination.exists() and destination.read_bytes() != data:
            raise FileExistsError(f"refusing to replace mismatched frozen prompt: {destination}")
        shutil.copyfile(source, destination)
        digest = sha256_bytes(data)
        prompt_words = len(data.decode("utf-8").split())
        if row["study"] == "experiment-2":
            frozen = experiment_2_metadata[row["source_id"]]
            expected = {
                "arm": "constrained",
                "condition": row["condition"],
                "payload_identity": row["identity"],
                "lanes": 2,
                "seed": row["seed"],
                "prompt_sha256": digest,
                "prompt_words": prompt_words,
            }
            observed = {key: frozen[key] for key in expected}
        else:
            frozen = experiment_4a_metadata[row["source_id"]]
            expected = {
                "condition": row["condition"],
                "payload_identity": row["identity"],
                "seed": row["seed"],
                "prompt_sha256": digest,
                "prompt_words": prompt_words,
            }
            observed = {key: frozen[key] for key in expected}
        if observed != expected:
            raise AssertionError(
                f"frozen metadata mismatch for {row['logical_id']}: {observed} != {expected}"
            )
        execution.append({"trial_id": trial_id, "prompt_file": f"frozen-prompts/{trial_id}.txt", "prompt_sha256": digest, "prompt_words": prompt_words})
        provenance.append({"trial_id": trial_id, **row, "source_sha256": digest, "prompt_words": prompt_words})
        expected_answer = ANSWER_A if row["identity"] == "A" else ANSWER_B if row["identity"] == "B" else None
        key.append({"trial_id": trial_id, "study": row["study"], "condition": row["condition"], "identity": row["identity"], "seed": row["seed"], "expected_answer": expected_answer})
    execution_path = ROOT / "execution-manifest.json"
    provenance_path = ROOT / "provenance-manifest.json"
    key_path = ROOT / "scoring-key.json"
    execution_path.write_text(json.dumps({"schema_version": 1, "packet_version": VERSION, "trials": execution}, indent=2) + "\n")
    provenance_path.write_text(json.dumps({"schema_version": 1, "selection_rule": "seeds 1 through 10 for paired signals; Experiment 2 controls 1 through 10; all five Experiment 4A controls; SHA-256 order independent of historical outcomes", "trials": provenance}, indent=2) + "\n")
    key_path.write_text(json.dumps({"schema_version": 1, "answer_A": ANSWER_A, "answer_B": ANSWER_B, "trials": key}, indent=2) + "\n")
    aggregate = hashlib.sha256()
    for trial in execution:
        aggregate.update(trial["trial_id"].encode())
        aggregate.update(b"\0")
        aggregate.update(trial["prompt_sha256"].encode())
        aggregate.update(b"\n")
    freeze = {
        "schema_version": 1,
        "packet_version": VERSION,
        "selection_frozen_before_external_execution": True,
        "paper_evidence_tag": "paper-evidence-freeze-v1",
        "paper_evidence_commit": subprocess.check_output(["git", "rev-list", "-n", "1", "paper-evidence-freeze-v1"], cwd=REPO, text=True).strip(),
        "trials": len(execution),
        "prompt_set_sha256": aggregate.hexdigest(),
        "manifest_sha256": {
            path.name: sha256_bytes(path.read_bytes())
            for path in (execution_path, provenance_path, key_path)
        },
    }
    (ROOT / "packet-freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    print(json.dumps({"packet_version": VERSION, "trials": len(rows), "experiment_2": 30, "experiment_4a": 25}, indent=2))


if __name__ == "__main__":
    main()
