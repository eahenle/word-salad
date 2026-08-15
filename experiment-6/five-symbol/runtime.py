#!/usr/bin/env python3
"""Hash-checked reuse of the frozen Experiment 4C no-tool Docker runtime."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SOURCE_ROOT = REPO / "experiment-4/dual-channel"
SOURCE_RUNTIME = SOURCE_ROOT / "runtime.py"
SOURCE_FREEZE = SOURCE_ROOT / "results/experiment-freeze.json"

freeze = json.loads(SOURCE_FREEZE.read_text())
actual = hashlib.sha256(SOURCE_RUNTIME.read_bytes()).hexdigest()
expected = freeze["source_hashes"]["runtime.py"]
if actual != expected:
    raise RuntimeError("frozen Experiment 4C runtime hash mismatch")

spec = importlib.util.spec_from_file_location("experiment_6_runtime", SOURCE_RUNTIME)
if spec is None or spec.loader is None:
    raise RuntimeError("could not load frozen runtime")
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
