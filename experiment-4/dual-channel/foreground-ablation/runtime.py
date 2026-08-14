#!/usr/bin/env python3
"""Load the exact frozen Experiment 4C no-tool runtime without altering it."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT.parent
SOURCE_RUNTIME = SOURCE_ROOT / "runtime.py"
SOURCE_FREEZE = SOURCE_ROOT / "results/experiment-freeze.json"

_freeze = json.loads(SOURCE_FREEZE.read_text())
_expected_hash = _freeze["source_hashes"]["runtime.py"]
_observed_hash = hashlib.sha256(SOURCE_RUNTIME.read_bytes()).hexdigest()
if _observed_hash != _expected_hash:
    raise RuntimeError("frozen Experiment 4C runtime hash mismatch")

_spec = importlib.util.spec_from_file_location("experiment_4c_frozen_runtime", SOURCE_RUNTIME)
if _spec is None or _spec.loader is None:
    raise RuntimeError("could not load frozen Experiment 4C runtime")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

IMAGE = _module.IMAGE
MODEL = _module.MODEL
EFFORT = _module.EFFORT
DISABLED_FEATURES = _module.DISABLED_FEATURES
atomic_bytes = _module.atomic_bytes
atomic_json = _module.atomic_json
parse_events = _module.parse_events
command = _module.command
run_subject = _module.run_subject

