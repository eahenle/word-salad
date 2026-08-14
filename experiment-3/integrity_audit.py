#!/usr/bin/env python3
"""Fail-closed integrity audit for the frozen Experiment 3 screening slate."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from runtime import MODELS, EFFORTS, atomic_json, cell_slug
from validate import validate


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent
    checks: dict[str, bool] = {}
    validate(root)
    checks["generator_validation_passed"] = True

    capability = json.loads((root / "results/capability-probe.json").read_text())
    requested = {(model, effort) for model in MODELS for effort in EFFORTS}
    probed = {(cell["model"], cell["reasoning"]) for cell in capability["cells"]}
    checks["all_exact_capability_cells_supported"] = (
        probed == requested and all(cell["status"] == "supported" for cell in capability["cells"])
    )
    isolation = json.loads((root / "results/isolation-validation.json").read_text())
    checks["isolation_validation_passed"] = bool(isolation.get("passed"))

    screening = json.loads((root / "results/screening-freeze.json").read_text())
    trace_mismatches = []
    prompt_mismatches = []
    infrastructure_errors = []
    broken_pipe_hits = []
    fresh_records = 0
    for slug, frozen in screening["fresh_cells"].items():
        for trial_id, digest in frozen.items():
            record_path = root / "completed" / slug / f"{trial_id}.json"
            record = json.loads(record_path.read_text())
            trace = root / record["trace_file"]
            stderr = root / record["stderr_file"]
            prompt = root / record["prompt_file"]
            fresh_records += 1
            if sha(trace) != digest or sha(trace) != record["runner"]["trace_sha256"]:
                trace_mismatches.append(f"{slug}/{trial_id}")
            if sha(prompt) != record["prompt_sha256"]:
                prompt_mismatches.append(f"{slug}/{trial_id}")
            error = (record["runner"].get("error") or {}).get("type")
            if error not in {None, "timeout"}:
                infrastructure_errors.append({"trial": f"{slug}/{trial_id}", "error": error})
            stderr_text = stderr.read_text(errors="replace").lower()
            if "broken pipe" in stderr_text or "connection reset" in stderr_text:
                broken_pipe_hits.append(f"{slug}/{trial_id}")
    checks["screening_fresh_record_count_473"] = fresh_records == 473
    checks["fresh_trace_hashes_match_freeze"] = not trace_mismatches
    checks["fresh_prompt_hashes_match"] = not prompt_mismatches
    checks["no_retry_eligible_infrastructure_errors"] = not infrastructure_errors
    checks["no_broken_pipe_or_connection_reset"] = not broken_pipe_hits

    anchor = json.loads((root / "results/anchor-freeze.json").read_text())
    anchor_mismatches = []
    anchor_slug = cell_slug("gpt-5.6-sol", "xhigh")
    for trial_id, digest in anchor["fresh_trace_hashes"].items():
        if sha(root / "traces" / anchor_slug / f"{trial_id}.jsonl") != digest:
            anchor_mismatches.append(trial_id)
    checks["anchor_trace_hashes_match_freeze"] = not anchor_mismatches

    reused = [json.loads(line) for line in (root / "results/reused-fixed-sol-xhigh.jsonl").read_text().splitlines()]
    reused_mismatches = []
    for record in reused:
        source_trace = root.parent / record["source_experiment"] / record["source_trace_file"]
        prompt = root / record["prompt_file"]
        if sha(source_trace) != record["runner"]["trace_sha256"] or sha(prompt) != record["prompt_sha256"]:
            reused_mismatches.append(record["neutral_id"])
    checks["reused_fixed_record_count_40"] = len(reused) == 40
    checks["reused_fixed_hashes_match"] = not reused_mismatches

    dirty_frozen = subprocess.run(
        ["git", "status", "--porcelain", "--", "multiplex-experiment", "experiment-1b", "experiment-2"],
        cwd=root.parent, capture_output=True, text=True, check=True,
    ).stdout.strip()
    checks["frozen_prior_experiment_worktrees_unchanged"] = not dirty_frozen
    checks["direct_api_calls_zero"] = (
        screening.get("direct_api_calls") == 0 and anchor.get("direct_api_calls") == 0
    )
    forbidden_names = [
        str(path.relative_to(root)) for path in root.rglob("*")
        if path.is_file() and path.name.lower() in {"auth.json", ".env"}
    ]
    checks["no_credentials_stored_in_experiment_tree"] = not forbidden_names
    result = {
        "passed": all(checks.values()),
        "checks": checks,
        "counts": {"fresh_screening": fresh_records, "reused_fixed_available": len(reused)},
        "trace_mismatches": trace_mismatches,
        "prompt_mismatches": prompt_mismatches,
        "anchor_mismatches": anchor_mismatches,
        "reused_mismatches": reused_mismatches,
        "infrastructure_errors": infrastructure_errors,
        "broken_pipe_hits": broken_pipe_hits,
        "forbidden_names": forbidden_names,
        "prior_experiment_dirty_paths": dirty_frozen.splitlines() if dirty_frozen else [],
        "isolation_boundary": "audited practical same-host Docker boundary, not cryptographic multi-host isolation",
    }
    atomic_json(root / "results/integrity-audit.json", result)
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
