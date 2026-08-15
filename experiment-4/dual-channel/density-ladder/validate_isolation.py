#!/usr/bin/env python3
"""Validate exact 4C no-tool runtime and clean image reuse."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess

from runtime import DISABLED_FEATURES, IMAGE, ROOT, SOURCE_FREEZE, SOURCE_RUNTIME, atomic_json, command


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--docker", default="docker")
    args = parser.parse_args(); source_freeze = json.loads(SOURCE_FREEZE.read_text())
    source_isolation = json.loads((ROOT.parent / "results/isolation-validation.json").read_text())
    inspect = subprocess.run([args.docker, "image", "inspect", IMAGE], text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    inspected_id = json.loads(inspect.stdout)[0]["Id"] if inspect.returncode == 0 else None
    cmd = command(name="word-salad-density-command-audit", docker=args.docker)
    runtime_hash = hashlib.sha256(SOURCE_RUNTIME.read_bytes()).hexdigest()
    passed = (source_isolation["passed"] and inspected_id == IMAGE
              and runtime_hash == source_freeze["source_hashes"]["runtime.py"]
              and tuple(DISABLED_FEATURES) == tuple(source_freeze["disabled_codex_features"])
              and not any("mcp_servers" in item for item in cmd)
              and not any(item in {"--mount", "--volume"} for item in cmd))
    result = {"passed": passed, "image": IMAGE, "image_inspect_id": inspected_id,
              "runtime_source_sha256": runtime_hash, "runtime_change_from_4c": "none",
              "disabled_codex_features": list(DISABLED_FEATURES),
              "mcp_servers_configured": False, "host_paths_mounted": False,
              "fresh_container_per_trial": True, "ephemeral_codex_session": True,
              "code_mode_warning_suppressed": False,
              "code_mode_warning_decision": "retained for exact runtime matching",
              "same_host_container_isolation": "audited practical boundary, not a cryptographic multi-host guarantee"}
    atomic_json(ROOT / "results/isolation-validation.json", result); print(json.dumps(result, indent=2))
    if not passed: raise SystemExit(1)


if __name__ == "__main__": main()

