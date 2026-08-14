#!/usr/bin/env python3
"""Fail-closed integrity audit for frozen Experiment 4A."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from runtime import CELLS, atomic_json, cell_slug
from validate_uniform import validate


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent
    checks: dict[str, bool] = {}
    validate(root)
    checks["generator_validation_passed"] = True
    refs = json.loads((root / "frozen-references.json").read_text())
    exp3 = root.parent / "experiment-3"
    checks["experiment3_freeze_hash_matches"] = sha(exp3 / "results/experiment-freeze.json") == refs["experiment_3"]["experiment_freeze_sha256"]
    checks["experiment3_confirmation_hash_matches"] = sha(exp3 / "results/confirmation-combined-trials.jsonl") == refs["experiment_3"]["confirmation_trials_sha256"]
    checks["experiment3_integrity_hash_matches"] = sha(exp3 / "results/integrity-audit.json") == refs["experiment_3"]["integrity_audit_sha256"]
    isolation = json.loads((root / "uniform/results/isolation-validation.json").read_text())
    checks["fresh_isolation_validation_passed"] = bool(isolation.get("passed"))
    capability = json.loads((root / "uniform/results/capability-probe.json").read_text())
    checks["exact_capability_cells_supported"] = (
        {(c["model"], c["reasoning"]) for c in capability["cells"]} == set(CELLS)
        and all(c["status"] == "supported" for c in capability["cells"])
        and not capability["substitution_performed"]
    )
    freeze = json.loads((root / "uniform/results/execution-freeze.json").read_text())
    trace_mismatches, prompt_mismatches, infrastructure_errors, broken_pipe_hits = [], [], [], []
    count = 0
    for slug, frozen in freeze["cells"].items():
        for trial_id, digest in frozen.items():
            record = json.loads((root / "uniform/completed" / slug / f"{trial_id}.json").read_text())
            trace, prompt, stderr = root / record["trace_file"], root / record["prompt_file"], root / record["stderr_file"]
            count += 1
            if sha(trace) != digest or sha(trace) != record["runner"]["trace_sha256"]:
                trace_mismatches.append(f"{slug}/{trial_id}")
            if sha(prompt) != record["prompt_sha256"]:
                prompt_mismatches.append(f"{slug}/{trial_id}")
            error = (record["runner"].get("error") or {}).get("type")
            if error not in {None, "timeout"}:
                infrastructure_errors.append({"trial": f"{slug}/{trial_id}", "error": error})
            lowered = stderr.read_text(errors="replace").lower()
            if "broken pipe" in lowered or "connection reset" in lowered:
                broken_pipe_hits.append(f"{slug}/{trial_id}")
    checks["fresh_trial_count_90"] = count == 90
    checks["trace_hashes_match_freeze"] = not trace_mismatches
    checks["prompt_hashes_match"] = not prompt_mismatches
    checks["no_retry_eligible_infrastructure_errors"] = not infrastructure_errors
    checks["no_broken_pipe_or_connection_reset"] = not broken_pipe_hits
    checks["direct_api_calls_zero"] = freeze.get("direct_api_calls") == 0
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "multiplex-experiment", "experiment-1b", "experiment-2", "experiment-3"],
                           cwd=root.parent, capture_output=True, text=True, check=True).stdout.strip()
    checks["frozen_prior_experiment_worktrees_unchanged"] = not dirty
    forbidden = [str(path.relative_to(root)) for path in root.rglob("*") if path.is_file() and path.name.lower() in {"auth.json", ".env"}]
    checks["no_credentials_stored"] = not forbidden
    result = {"passed": all(checks.values()), "checks": checks, "counts": {"fresh_trials": count},
              "trace_mismatches": trace_mismatches, "prompt_mismatches": prompt_mismatches,
              "infrastructure_errors": infrastructure_errors, "broken_pipe_hits": broken_pipe_hits,
              "forbidden_names": forbidden, "prior_experiment_dirty_paths": dirty.splitlines() if dirty else [],
              "isolation_boundary": "audited practical same-host Docker boundary, not cryptographic multi-host isolation"}
    atomic_json(root / "uniform/results/integrity-audit.json", result)
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
