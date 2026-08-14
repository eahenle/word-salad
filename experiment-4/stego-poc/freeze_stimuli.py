#!/usr/bin/env python3
"""Freeze the pre-inference Experiment 4B protocol and prompt hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from cover_generator import DEFENSES, VERSION
from poc_runtime import EFFORT, IMAGE, MODEL
from validate import validate


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(); root = args.root.resolve()
    validation = validate(root)
    git_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True,
                                capture_output=True, check=True).stdout.strip()
    prompts = {record["neutral_id"]: record["prompt_sha256"]
               for cohort in validation["sets"] for record in cohort["records"]}
    freeze = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(), "git_commit_before_4b": git_commit,
              "generator_version": VERSION, "model": MODEL, "reasoning": EFFORT,
              "container_image": IMAGE, "python_version": sys.version,
              "platform": platform.platform(), "development_gate": {
                  "proceed_if": "at least 1/2 complete A/B pairs OR at least 3/4 expected individuals",
                  "counterpart_marker_errors_allowed": 0},
              "heldout_execution": {"topics": 5, "conditions": 4, "defenses": list(DEFENSES),
                                    "scheduled_trials": 20, "score_only_after_complete": True},
              "prompt_hashes": dict(sorted(prompts.items())),
              "source_hashes": {name: sha256(root / name) for name in (
                  "README.md", "cover_generator.py", "validate.py", "poc_runtime.py",
                  "container/Dockerfile", "container/credential-gate-q4",
                  "container/disabled-subject-shell", "container/marker_server.py")}}
    path = root / "results/stimulus-freeze.json"; content = json.dumps(freeze, indent=2) + "\n"
    if path.exists():
        prior = json.loads(path.read_text()); comparison = dict(freeze); comparison["frozen_at_utc"] = prior["frozen_at_utc"]
        if prior != comparison: raise RuntimeError("stimulus freeze exists and current protocol differs")
        print(f"verified existing freeze: {path}"); return
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
    print(f"froze {len(prompts)} prompt hashes at {path}")


if __name__ == "__main__":
    main()
