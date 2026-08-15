#!/usr/bin/env python3
"""Freeze the complete staged density-ladder method before its first inference."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone

from generate import CONDITIONS, DENSITIES, FRAME, ROOT, SEED_VERSION, SOURCE_ROOT, TOPICS
from runtime import DISABLED_FEATURES, EFFORT, IMAGE, MODEL, SOURCE_RUNTIME, atomic_json
from validate import SOURCE_4C_COMMIT, SOURCE_4C1_COMMIT


SOURCES = ("README.md", "runtime.py", "generate.py", "validate.py", "validate_isolation.py",
           "freeze_protocol.py", "freeze_stage.py", "run_stage.py", "score_stage.py",
           "trace_audit.py", "analyze.py", "integrity_audit.py")


def sha256(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT.parents[2], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode: raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def main() -> None:
    tags = {"experiment_4c": ("experiment-4c-dual-channel-negative-gate", SOURCE_4C_COMMIT),
            "experiment_4c1": ("experiment-4c1-foreground-coherence-null", SOURCE_4C1_COMMIT)}
    references = {}
    for name, (tag, expected) in tags.items():
        observed = git("rev-parse", f"{tag}^{{}}")
        if observed != expected: raise RuntimeError(f"{tag} resolves to {observed}, expected {expected}")
        references[name] = {"tag": tag, "commit": expected}
    references["source_4c_tree"] = git("rev-parse", "experiment-4c-dual-channel-negative-gate^{commit}:experiment-4/dual-channel")
    atomic_json(ROOT / "frozen-references.json", references)
    protocol = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": "4C.2", "design": "staged incoherent-interference density ladder",
        "repository_commit_before_changes": git("rev-parse", "HEAD"),
        "model": MODEL, "reasoning": EFFORT, "image": IMAGE, "frame": FRAME,
        "topics": list(TOPICS), "conditions": list(CONDITIONS), "trials_per_stage": 9,
        "densities": DENSITIES, "seed_version": SEED_VERSION,
        "stage_order": ["d125", "d250"], "d500_not_authorized_in_initial_ladder": True,
        "decision_rules": {
            "d125": {"clean_gate_pass": "stop and confirm 12.5% with fresh seeds",
                     "clean_complete_null": "advance to d250",
                     "partial_recovery": "stop and consider independent d125 replication",
                     "control_target_selection": "stop for control audit"},
            "d250": {"clean_gate_pass": "stop; boundary lies above d125 and at or below d250",
                     "clean_complete_null": "stop; consider d500 only as a later frozen experiment",
                     "partial_recovery": "stop and consider independent d250 replication",
                     "control_target_selection": "stop for control audit"}},
        "gate": {"complete_ab_pairs_at_least": 2, "scrambled_target_selections_exactly": 0},
        "uniform_carrier_masks": True, "condition_masks_matched_within_topic": True,
        "nested_nonsignal_samples_across_densities": True,
        "source_4c_commit": SOURCE_4C_COMMIT, "source_4c1_commit": SOURCE_4C1_COMMIT,
        "frozen_runtime_sha256": sha256(SOURCE_RUNTIME),
        "source_hashes": {name: sha256(ROOT / name) for name in SOURCES},
        "disabled_codex_features": list(DISABLED_FEATURES), "tools_exposed": False,
        "mcp_servers_configured": False, "direct_api_used": False,
        "code_mode_warning_suppressed": False,
        "python_version": platform.python_version(), "platform": platform.platform()}
    path = ROOT / "results/protocol-freeze.json"
    if path.exists():
        previous = json.loads(path.read_text()); comparable = dict(protocol)
        comparable["frozen_at_utc"] = previous["frozen_at_utc"]
        if previous != comparable: raise RuntimeError("existing protocol freeze differs")
    else: atomic_json(path, protocol)
    print(json.dumps({"frozen": True, "stages": protocol["stage_order"]}, indent=2))


if __name__ == "__main__": main()

