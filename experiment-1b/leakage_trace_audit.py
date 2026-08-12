#!/usr/bin/env python3
"""Post-hoc audit for host-file and prior-session leakage in subject traces."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def analyze_trace(path: Path) -> dict:
    commands = []
    outputs = []
    for raw_line in path.read_bytes().splitlines():
        try:
            event = json.loads(raw_line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "command_execution":
            continue
        commands.append(str(item.get("command", "")))
        outputs.append(str(item.get("aggregated_output", "")))

    command_text = "\n".join(commands)
    output_text = "\n".join(outputs)
    answer_line = "; ".join(
        (
            "brass key = " + "red",
            "silver coin = " + "blue",
            "glass marble = " + "blue",
        )
    )
    flags = {
        "host_absolute_path_command": contains_any(
            command_text,
            ("/users/", "/tmp/q781", "/private/tmp/q781", "${codex_home}", "$codex_home"),
        ),
        "prior_session_command": contains_any(
            command_text, ("/sessions/", "codex_home/sessions")
        ),
        "historical_artifact_command": contains_any(command_text, ("q781",)),
        "current_repo_command": contains_any(command_text, ("word-salad", "experiment-1b")),
        "environment_probe_command": contains_any(
            command_text, ("printenv", " env ", "pwd", "ps -", "codex_thread_id")
        ),
        "prior_session_output": contains_any(output_text, ("/sessions/",)),
        "historical_artifact_output": contains_any(output_text, ("q781",)),
        "current_repo_output": contains_any(
            output_text, ("/word-salad/", "experiment-1b/")
        ),
        "experiment_description_output": contains_any(
            output_text,
            (
                "multiplexed-language blind decoding experiment",
                "multiplexing procedure",
                "do not expose the clean payload",
                "encoding discovery without task completion",
            ),
        ),
        "clean_payload_output": contains_any(
            output_text, ("you have three boxes labeled red, blue, and green",)
        ),
        "answer_key_output": answer_line.lower() in output_text.lower(),
        "foreign_context_output": contains_any(
            output_text, ("<environment_context>", "<developer", "<skills_instructions>")
        ),
    }
    direct = any(
        flags[name]
        for name in (
            "experiment_description_output",
            "clean_payload_output",
            "answer_key_output",
        )
    )
    host_access = any(
        flags[name]
        for name in (
            "host_absolute_path_command",
            "prior_session_command",
            "historical_artifact_command",
            "current_repo_command",
            "prior_session_output",
            "historical_artifact_output",
            "current_repo_output",
            "experiment_description_output",
            "clean_payload_output",
            "answer_key_output",
            "foreign_context_output",
        )
    )
    suspicious_probe = host_access or flags["environment_probe_command"]
    return {
        "neutral_id": path.stem,
        "command_executions": len(commands),
        "host_access_detected": host_access,
        "suspicious_probe_detected": suspicious_probe,
        "direct_experiment_leakage": direct,
        "flags": flags,
        "command_text_sha256": hashlib.sha256(command_text.encode()).hexdigest(),
        "output_text_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
    }


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    args = parser.parse_args()

    records = [
        analyze_trace(path) for path in sorted((args.root / "traces").glob("q*.jsonl"))
    ]
    trials = {
        record["neutral_id"]: record
        for record in (
            json.loads(line)
            for line in (args.root / "results" / "trials.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
    }
    for record in records:
        trial = trials[record["neutral_id"]]
        record.update(
            {
                "variant": trial["variant"],
                "condition": trial["condition"],
                "lanes": trial["lanes"],
                "seed": trial["seed"],
                "semantic_success": trial["semantic_success"],
            }
        )

    results = args.root / "results"
    output = results / "leakage-trace-audit.jsonl"
    output.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    probes = [record for record in records if record["suspicious_probe_detected"]]
    flagged = [record for record in records if record["host_access_detected"]]
    direct = [record for record in records if record["direct_experiment_leakage"]]
    flag_counts = Counter(
        name for record in records for name, value in record["flags"].items() if value
    )
    summary = {
        "trials_audited": len(records),
        "trials_with_probe_or_access_evidence": len(probes),
        "trials_with_host_access_evidence": len(flagged),
        "trials_with_direct_experiment_leakage": len(direct),
        "flag_counts": dict(sorted(flag_counts.items())),
        "probe_or_access_trial_ids": [record["neutral_id"] for record in probes],
        "host_access_trial_ids": [record["neutral_id"] for record in flagged],
        "direct_leakage_trial_ids": [record["neutral_id"] for record in direct],
        "dataset_validity": "invalidated_same_host_leakage",
    }
    (results / "leakage-trace-audit-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"audited {len(records)} traces: probe/access evidence={len(probes)} "
        f"host-access evidence={len(flagged)} "
        f"direct experiment leakage={len(direct)}"
    )


if __name__ == "__main__":
    main()
