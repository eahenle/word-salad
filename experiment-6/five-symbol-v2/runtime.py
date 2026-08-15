#!/usr/bin/env python3
"""Hash-checked reuse of the frozen Experiment 4C no-tool Docker runtime."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SOURCE = REPO / "experiment-4/dual-channel/runtime.py"
FREEZE = REPO / "experiment-4/dual-channel/results/experiment-freeze.json"
expected = json.loads(FREEZE.read_text())["source_hashes"]["runtime.py"]
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != expected:
    raise RuntimeError("frozen Experiment 4C runtime hash mismatch")
spec = importlib.util.spec_from_file_location("experiment_6_v2_runtime", SOURCE)
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
run_subject = module.run_subject
