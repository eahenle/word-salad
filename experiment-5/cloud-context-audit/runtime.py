#!/usr/bin/env python3
"""Hash-checked reuse of the exact frozen Experiment 4C no-tool runtime."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
SOURCE_ROOT = REPO_ROOT / "experiment-4/dual-channel"
SOURCE_RUNTIME = SOURCE_ROOT / "runtime.py"
SOURCE_FREEZE = SOURCE_ROOT / "results/experiment-freeze.json"
EXPECTED_PARENT = "92e59750a34edf739c1ae1bc1b820012ca0eeb8a"

freeze = json.loads(SOURCE_FREEZE.read_text())
actual_hash = hashlib.sha256(SOURCE_RUNTIME.read_bytes()).hexdigest()
expected_hash = freeze["source_hashes"]["runtime.py"]
if actual_hash != expected_hash:
    raise RuntimeError("frozen Experiment 4C runtime hash mismatch")
if freeze.get("repository_commit_before_experiment_changes") != EXPECTED_PARENT:
    raise RuntimeError("unexpected Experiment 4C provenance")

spec = importlib.util.spec_from_file_location("experiment_5_cloud_runtime", SOURCE_RUNTIME)
if spec is None or spec.loader is None:
    raise RuntimeError("could not load frozen Experiment 4C runtime")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

IMAGE = module.IMAGE
MODEL = module.MODEL
EFFORT = module.EFFORT
DISABLED_FEATURES = module.DISABLED_FEATURES
atomic_bytes = module.atomic_bytes
atomic_json = module.atomic_json
command = module.command
run_subject = module.run_subject
