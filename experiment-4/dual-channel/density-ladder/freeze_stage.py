#!/usr/bin/env python3
"""Generate, validate, and freeze one preregistered density stage."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from generate import DENSITIES, ROOT, build, write
from runtime import atomic_json
from validate import validate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("density", choices=("d125", "d250"))
    density_id = parser.parse_args().density
    protocol = json.loads((ROOT / "results/protocol-freeze.json").read_text())
    if density_id == "d250":
        decision_path = ROOT / "development/d125/results/development-gate.json"
        if not decision_path.exists() or not json.loads(decision_path.read_text()).get("next_stage_authorized"):
            raise RuntimeError("d250 is not authorized by the frozen d125 result")
    write(density_id); validation = validate(density_id); stage = ROOT / "development" / density_id
    atomic_json(stage / "results/invariants.json", validation)
    records = build(density_id); manifest = []
    for row in records:
        manifest.append({key: row[key] for key in ("trial_id", "density_id", "topic", "condition",
            "source_trial_id", "hidden_identity", "expected_answer", "signal_positions",
            "document_sha256", "prompt_sha256", "configuration", "carrier_seed", "noise_order_seed")})
    atomic_json(stage / "manifest.json", manifest)
    freeze = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(), "density_id": density_id,
              "configuration": DENSITIES[density_id], "scheduled_trials": 9,
              "protocol_freeze_sha256": __import__("hashlib").sha256((ROOT / "results/protocol-freeze.json").read_bytes()).hexdigest(),
              "prompt_hashes": {row["trial_id"]: row["prompt_sha256"] for row in manifest},
              "document_hashes": {row["trial_id"]: row["document_sha256"] for row in manifest},
              "score_after_execution_freeze": True, "direct_api_used": False}
    path = stage / "results/stage-freeze.json"
    if path.exists():
        old = json.loads(path.read_text()); comparable = dict(freeze); comparable["frozen_at_utc"] = old["frozen_at_utc"]
        if old != comparable: raise RuntimeError("existing stage freeze differs")
    else: atomic_json(path, freeze)
    print(json.dumps({"stage_frozen": density_id, "trials": 9}, indent=2))


if __name__ == "__main__": main()

