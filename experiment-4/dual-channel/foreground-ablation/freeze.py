#!/usr/bin/env python3
"""Freeze 4C.1 prompt hashes, source lineage, runtime, and gate before inference."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from generate_decohered import CONDITIONS, FRAME, ROOT, SEED_VERSION, SOURCE_ROOT, TOPICS, build, write_outputs
from runtime import DISABLED_FEATURES, EFFORT, IMAGE, MODEL, SOURCE_RUNTIME, atomic_json
from validate import SOURCE_COMMIT, SOURCE_TAG, validate


SOURCES = ("README.md", "generate_decohered.py", "validate.py", "runtime.py",
           "validate_isolation.py", "freeze.py", "run.py", "score.py", "analyze.py")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*arguments: str) -> str:
    result = subprocess.run(["git", *arguments], cwd=ROOT.parents[2], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def main() -> None:
    write_outputs(); invariants = validate(); records = build()
    if git("rev-parse", f"{SOURCE_TAG}^{{}}") != SOURCE_COMMIT:
        raise RuntimeError("frozen 4C tag no longer resolves to the preregistered commit")
    source_tree = git("rev-parse", f"{SOURCE_TAG}^{{commit}}:experiment-4/dual-channel")
    references = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_4c": {"commit": SOURCE_COMMIT, "tag": SOURCE_TAG,
                          "tree": source_tree, "path": "experiment-4/dual-channel"},
        "source_experiment_freeze_sha256": sha256(SOURCE_ROOT / "results/experiment-freeze.json"),
        "source_development_gate_sha256": sha256(SOURCE_ROOT / "results/development-gate.json"),
        "source_integrity_audit_sha256": sha256(SOURCE_ROOT / "results/integrity-audit.json"),
    }
    atomic_json(ROOT / "frozen-references.json", references)
    atomic_json(ROOT / "results/invariants.json", invariants)
    manifest = []
    for record in records:
        manifest.append({
            "trial_id": record["trial_id"], "source_trial_id": record["source_trial_id"],
            "topic": record["topic"], "condition": record["condition"],
            "hidden_identity": record["hidden_identity"], "expected_answer": record["expected_answer"],
            "prompt_sha256": record["prompt_sha256"], "document_sha256": record["document_sha256"],
            "source_document_sha256": record["source_document_sha256"],
            "document_words": record["document_words"], "signal_words": record["signal_words"],
            "signal_density": record["signal_density"], "signal_positions": record["signal_positions"],
            "seed": record["seed"],
        })
    atomic_json(ROOT / "development/manifest.json", manifest)
    freeze = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": "4C.1", "phase": "initial_foreground_coherence_ablation",
        "repository_commit_before_experiment_changes": git("rev-parse", "HEAD"),
        "source_experiment_commit": SOURCE_COMMIT, "source_experiment_tag": SOURCE_TAG,
        "model": MODEL, "reasoning": EFFORT, "image": IMAGE,
        "frame": FRAME, "custom_developer_instructions": None,
        "scheduled_trials": 9, "topics": list(TOPICS), "conditions": list(CONDITIONS),
        "replicates": [1], "seed_version": SEED_VERSION,
        "manipulation": "uniform deterministic permutation of nonsignal words only",
        "score_only_after_all_responses_freeze": True,
        "development_gate": {"complete_ab_pairs_at_least": 2,
                             "scrambled_control_target_selections_exactly": 0},
        "primary_endpoint": "complete paired answer identity: A -> Rowan and B -> Mira",
        "prompt_hashes": {row["trial_id"]: row["prompt_sha256"] for row in manifest},
        "document_hashes": {row["trial_id"]: row["document_sha256"] for row in manifest},
        "source_document_hashes": {row["trial_id"]: row["source_document_sha256"] for row in manifest},
        "source_hashes": {source: sha256(ROOT / source) for source in SOURCES},
        "frozen_runtime_sha256": sha256(SOURCE_RUNTIME),
        "disabled_codex_features": list(DISABLED_FEATURES),
        "code_mode_warning_suppressed": False,
        "tools_exposed": False, "mcp_servers_configured": False,
        "direct_api_used": False, "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
    path = ROOT / "results/experiment-freeze.json"
    if path.exists():
        previous = json.loads(path.read_text()); comparable = dict(freeze)
        comparable["frozen_at_utc"] = previous["frozen_at_utc"]
        if previous != comparable:
            raise RuntimeError("existing experiment freeze differs")
    else:
        atomic_json(path, freeze)
    print(json.dumps({"frozen": True, "trials": len(manifest),
                      "source_commit": SOURCE_COMMIT}, indent=2))


if __name__ == "__main__":
    main()

