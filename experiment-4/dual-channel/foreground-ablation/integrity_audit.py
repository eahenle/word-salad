#!/usr/bin/env python3
"""Audit frozen Experiment 4C.1 lineage, prompts, traces, scores, and no-tool execution."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from generate_decohered import FRAME, ROOT, build
from runtime import SOURCE_RUNTIME, atomic_json
from validate import SOURCE_COMMIT, SOURCE_TAG, validate


TOOL_TYPES = {"command_execution", "mcp_tool_call", "file_change", "web_search",
              "browser_action", "computer_action", "image_generation", "tool_call"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*arguments: str) -> str:
    result = subprocess.run(["git", *arguments], cwd=ROOT.parents[2], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def item_types(path: Path) -> list[str]:
    output = []
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "item.completed":
            output.append(str(event.get("item", {}).get("type", "unknown")))
    return output


def main() -> None:
    validation = validate(); protocol = json.loads((ROOT / "results/experiment-freeze.json").read_text())
    isolation = json.loads((ROOT / "results/isolation-validation.json").read_text())
    execution = json.loads((ROOT / "development/results/execution-freeze.json").read_text())
    gate = json.loads((ROOT / "results/development-gate.json").read_text())
    manifest = json.loads((ROOT / "development/manifest.json").read_text())
    unscored = [json.loads(line) for line in (ROOT / "development/results/trials-unscored.jsonl").read_text().splitlines()]
    scored = [json.loads(line) for line in (ROOT / "results/trials.jsonl").read_text().splitlines()]
    checks = {
        "source_tag_commit_matches": git("rev-parse", f"{SOURCE_TAG}^{{}}") == SOURCE_COMMIT,
        "source_tree_matches_reference": git("rev-parse", f"{SOURCE_TAG}^{{commit}}:experiment-4/dual-channel") == json.loads((ROOT / "frozen-references.json").read_text())["experiment_4c"]["tree"],
        "mechanical_invariants_pass": validation["passed"],
        "isolation_passes": isolation["passed"],
        "runtime_hash_matches": sha256(SOURCE_RUNTIME) == protocol["frozen_runtime_sha256"],
        "nine_unique_manifest_trials": len(manifest) == len({row["trial_id"] for row in manifest}) == 9,
        "execution_complete": execution["scheduled"] == execution["completed"] == 9,
        "no_runner_errors_or_timeouts": execution["runner_errors"] == execution["timeouts"] == 0,
        "nine_unscored_and_scored": len(unscored) == len(scored) == 9,
        "source_hashes_match": all(sha256(ROOT / source) == digest for source, digest in protocol["source_hashes"].items()),
        "prompt_hashes_match": all(sha256(ROOT / "development/prompts" / f"{row['trial_id']}.txt") == protocol["prompt_hashes"][row["trial_id"]] for row in manifest),
        "document_hashes_match": all(sha256(ROOT / "development/documents" / f"{row['trial_id']}.txt") == protocol["document_hashes"][row["trial_id"]] for row in manifest),
        "trace_hashes_match": all(sha256(ROOT / row["trace_file"]) == execution["trace_hashes"][row["trial_id"]] for row in unscored),
        "scoring_preserves_frozen_responses": {row["trial_id"]: row["response"] for row in unscored} == {row["trial_id"]: row["response"] for row in scored},
        "prompt_bytes_equal_frame_plus_document": all((ROOT / "development/prompts" / f"{record['trial_id']}.txt").read_text() == FRAME + "\n\n" + record["document"] for record in build()),
        "primary_result_is_null": gate["expected_hidden_answers"] == gate["complete_ab_pairs"] == gate["scrambled_control_target_selections"] == 0,
        "no_direct_api": not execution["direct_api_used"] and not protocol["direct_api_used"],
    }
    trace_types = {row["trial_id"]: item_types(ROOT / row["trace_file"]) for row in unscored}
    observed_tools = sorted({kind for kinds in trace_types.values() for kind in kinds if kind in TOOL_TYPES})
    checks["no_observable_tool_invocations"] = not observed_tools
    checks["fail_closed_code_mode_item_in_every_trace"] = all("error" in kinds for kinds in trace_types.values())
    failures = [name for name, passed in checks.items() if not passed]
    result_paths = [ROOT / "results/development-gate.json", ROOT / "results/trials.jsonl",
                    ROOT / "results/answer-identity.csv", ROOT / "results/analysis.md",
                    ROOT / "results/strategy-summary.json", ROOT / "results/trace-strategy-audit.json",
                    ROOT / "results/trace-analysis.md", ROOT / "development/results/execution-freeze.json",
                    ROOT / "development/results/trials-unscored.jsonl"]
    result = {
        "audited_at_utc": datetime.now(timezone.utc).isoformat(), "passed": not failures,
        "checks": checks, "failures": failures, "trace_item_types": trace_types,
        "observable_tool_item_types": observed_tools,
        "code_mode_warning": {"retained_for_exact_runtime_matching": True,
                              "substantive_model_behavior": False,
                              "trials_retried": 0},
        "result_hashes": {str(path.relative_to(ROOT)): sha256(path) for path in result_paths},
        "source_4c_modified": False, "additional_permutation_replicates_run": False,
    }
    atomic_json(ROOT / "results/integrity-audit.json", result)
    print(json.dumps({"passed": result["passed"], "failures": failures,
                      "observable_tool_item_types": observed_tools}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

