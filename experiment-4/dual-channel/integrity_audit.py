#!/usr/bin/env python3
"""Audit the frozen 4C protocol, stimuli, executions, scoring, and trace item types."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from cover_generator import FRAME, build
from runtime import atomic_json
from validate import ROOT, validate


TOOL_ITEM_TYPES = {
    "command_execution", "mcp_tool_call", "file_change", "web_search",
    "browser_action", "computer_action", "image_generation", "tool_call",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace_item_types(path: Path) -> Counter:
    counts = Counter()
    for line in path.read_bytes().splitlines():
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if event.get("type") == "item.completed":
            counts[str(event.get("item", {}).get("type", "unknown"))] += 1
    return counts


def main() -> None:
    validation = validate()
    protocol = json.loads((ROOT / "results/experiment-freeze.json").read_text())
    isolation = json.loads((ROOT / "results/isolation-validation.json").read_text())
    execution = json.loads((ROOT / "development/results/execution-freeze.json").read_text())
    gate = json.loads((ROOT / "results/development-gate.json").read_text())
    manifest = json.loads((ROOT / "development/manifest.json").read_text())
    unscored = [json.loads(line) for line in (ROOT / "development/results/trials-unscored.jsonl").read_text().splitlines()]
    scored = [json.loads(line) for line in (ROOT / "results/trials.jsonl").read_text().splitlines()]
    checks = {}
    checks["mechanical_validation_passed"] = validation["passed"]
    checks["isolation_validation_passed"] = isolation["passed"]
    checks["exact_clean_image"] = isolation["image"] == protocol["image"]
    checks["twelve_unique_manifest_trials"] = len(manifest) == len({row["trial_id"] for row in manifest}) == 12
    checks["twelve_unscored_and_scored_trials"] = len(unscored) == len(scored) == 12
    checks["execution_complete"] = execution["scheduled"] == execution["completed"] == 12
    checks["no_runner_errors_or_timeouts"] = execution["runner_errors"] == execution["timeouts"] == 0
    checks["gate_failed_and_heldout_forbidden"] = not gate["passed"] and not gate["heldout_authorized"]
    source_hashes = {source: sha256(ROOT / source) for source in protocol["source_hashes"]}
    checks["frozen_source_hashes_match"] = source_hashes == protocol["source_hashes"]
    prompt_hashes = {row["trial_id"]: sha256(ROOT / "development/prompts" / f"{row['trial_id']}.txt") for row in manifest}
    document_hashes = {row["trial_id"]: sha256(ROOT / "development/documents" / f"{row['trial_id']}.txt") for row in manifest}
    checks["frozen_prompt_hashes_match"] = prompt_hashes == protocol["prompt_hashes"]
    checks["frozen_document_hashes_match"] = document_hashes == protocol["document_hashes"]
    trace_hashes = {row["trial_id"]: sha256(ROOT / row["trace_file"]) for row in unscored}
    checks["frozen_trace_hashes_match"] = trace_hashes == execution["trace_hashes"]
    completed_by_id = {row["trial_id"]: row for row in unscored}
    checks["unscored_records_match_completed_files"] = all(
        completed_by_id[row["trial_id"]] == json.loads((ROOT / "development/completed" / f"{row['trial_id']}.json").read_text())
        for row in manifest
    )
    scored_by_id = {row["trial_id"]: row for row in scored}
    checks["scored_records_preserve_frozen_responses"] = all(
        scored_by_id[trial_id]["response"] == record["response"] for trial_id, record in completed_by_id.items()
    )
    generated = {record["trial_id"]: record for record in build()}
    checks["prompt_bytes_equal_frame_plus_document"] = all(
        (ROOT / "development/prompts" / f"{trial_id}.txt").read_text() == FRAME + "\n\n" + record["document"]
        for trial_id, record in generated.items()
    )
    item_counts = {trial_id: dict(trace_item_types(ROOT / record["trace_file"]))
                   for trial_id, record in completed_by_id.items()}
    observed_tool_types = sorted({item_type for counts in item_counts.values() for item_type in counts
                                  if item_type in TOOL_ITEM_TYPES})
    checks["no_observable_tool_invocation_items"] = not observed_tool_types
    checks["runtime_error_item_present_in_every_trace"] = all(counts.get("error") == 1 for counts in item_counts.values())
    failures = [name for name, passed in checks.items() if not passed]
    result_paths = [
        ROOT / "results/development-gate.json", ROOT / "results/trials.jsonl",
        ROOT / "results/answer-identity.csv", ROOT / "results/control-summary.json",
        ROOT / "results/analysis.md", ROOT / "results/strategy-summary.json",
        ROOT / "development/results/execution-freeze.json",
        ROOT / "development/results/trials-unscored.jsonl",
    ]
    result = {
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": not failures, "checks": checks, "failures": failures,
        "trace_item_type_counts": item_counts,
        "observable_tool_item_types": observed_tool_types,
        "runtime_artifact": {
            "item_type": "error", "trials": 12,
            "message": "Code Mode is unavailable because code-mode host is disabled. Code mode will fail closed; enable `features.code_mode_host` and install `codex-code-mode-host`.",
            "interpretation": "standardized fail-closed initialization item; not an observable tool invocation",
            "trials_retried": 0,
        },
        "result_hashes": {str(path.relative_to(ROOT)): sha256(path) for path in result_paths},
        "historical_datasets_modified": False,
        "heldout_executed": False,
    }
    atomic_json(ROOT / "results/integrity-audit.json", result)
    print(json.dumps({"passed": result["passed"], "failures": failures,
                      "observable_tool_item_types": observed_tool_types}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

