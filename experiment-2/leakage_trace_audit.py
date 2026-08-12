#!/usr/bin/env python3
"""Audit Experiment 2 command traces for observable host or experiment leakage."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def has(text: str, values: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(value.lower() in lowered for value in values)


def analyze(path: Path) -> dict:
    commands, outputs = [], []
    for line in path.read_bytes().splitlines():
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "command_execution":
            commands.append(str(item.get("command", "")))
            outputs.append(str(item.get("aggregated_output", "")))
    command_text, output_text = "\n".join(commands), "\n".join(outputs)
    flags = {
        "host_absolute_path_command": has(command_text, ("/users/", "/private/tmp/", "/sessions/")),
        "experiment_artifact_command": has(
            command_text,
            ("word-salad", "experiment-1", "experiment-2", "simulation-validation", "payload_a"),
        ),
        "environment_probe_command": has(
            command_text, ("printenv", " env ", "pwd", "ps -", "codex_thread_id", "/proc/")
        ),
        "host_or_experiment_output": has(
            output_text,
            ("/users/ahenle/word-salad", "experiment-1b/", "experiment-1c/", "experiment-2/"),
        ),
        "experiment_description_output": has(
            output_text,
            (
                "paired equal-multiset ordered payloads", "answer identity", "tool-less model",
                "surface-normalization matrix", "multiplexed-language blind decoding experiment",
            ),
        ),
        "foreign_context_output": has(
            output_text, ("<environment_context>", "<developer", "<skills_instructions>")
        ),
        "reconstructed_payload_output": has(
            output_text,
            ("you have three boxes labeled red, blue, and green", "perform the six operations"),
        ),
    }
    access_attempt = any(flags[name] for name in (
        "host_absolute_path_command", "experiment_artifact_command", "environment_probe_command"
    ))
    host_access = any(flags[name] for name in (
        "host_or_experiment_output", "experiment_description_output", "foreign_context_output"
    ))
    return {
        "neutral_id": path.stem, "command_executions": len(commands),
        "host_access_attempted": access_attempt, "host_access_detected": host_access,
        "direct_experiment_leakage": host_access,
        "behavioral_reconstruction_output": flags["reconstructed_payload_output"],
        "flags": flags,
        "command_text_sha256": hashlib.sha256(command_text.encode()).hexdigest(),
        "output_text_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
    }


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    args = parser.parse_args()
    trials = {
        row["neutral_id"]: row for row in (
            json.loads(line) for line in (args.root / "results" / "trials.jsonl").read_text().splitlines()
            if line.strip()
        )
    }
    rows = []
    for path in sorted((args.root / "traces").glob("r*.jsonl")):
        row = analyze(path)
        trial = trials[row["neutral_id"]]
        row.update({key: trial[key] for key in (
            "arm", "condition", "payload_identity", "lanes", "seed", "semantic_success"
        )})
        rows.append(row)
    results = args.root / "results"
    (results / "leakage-trace-audit.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    flag_counts = Counter(
        name for row in rows for name, value in row["flags"].items() if value
    )
    attempted = [row["neutral_id"] for row in rows if row["host_access_attempted"]]
    detected = [row["neutral_id"] for row in rows if row["host_access_detected"]]
    reconstructed = [
        row["neutral_id"] for row in rows if row["behavioral_reconstruction_output"]
    ]
    summary = {
        "trials_audited": len(rows), "trials_with_host_access_attempts": len(attempted),
        "trials_with_host_access_evidence": len(detected),
        "trials_with_direct_experiment_leakage": len(detected),
        "trials_with_reconstructed_payload_in_tool_output": len(reconstructed),
        "flag_counts": dict(sorted(flag_counts.items())),
        "host_access_attempt_trial_ids": attempted, "host_access_trial_ids": detected,
        "reconstructed_payload_trial_ids": reconstructed,
        "dataset_validity": "no_observed_host_leakage" if not detected else "invalidated_direct_leakage",
    }
    (results / "leakage-trace-audit-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
