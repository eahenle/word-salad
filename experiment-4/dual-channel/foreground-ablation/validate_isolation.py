#!/usr/bin/env python3
"""Verify exact reuse of the frozen 4C no-tool image and command."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from runtime import DISABLED_FEATURES, IMAGE, ROOT, SOURCE_FREEZE, SOURCE_RUNTIME, atomic_json, command


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", default="docker"); args = parser.parse_args()
    source_freeze = json.loads(SOURCE_FREEZE.read_text())
    source_isolation = json.loads((ROOT.parent / "results/isolation-validation.json").read_text())
    inspect = subprocess.run([args.docker, "image", "inspect", IMAGE], text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    inspected_id = json.loads(inspect.stdout)[0]["Id"] if inspect.returncode == 0 else None
    cmd = command(name="word-salad-q4c1-command-audit", docker=args.docker)
    required_disabled = {"shell_tool", "unified_exec", "browser_use", "computer_use",
                         "apps", "plugins", "view_image", "goals", "code_mode", "code_mode_host"}
    passed = (
        source_isolation["passed"] and source_isolation["image"] == IMAGE
        and inspected_id == IMAGE
        and hashlib.sha256(SOURCE_RUNTIME.read_bytes()).hexdigest() == source_freeze["source_hashes"]["runtime.py"]
        and tuple(source_freeze["disabled_codex_features"]) == tuple(DISABLED_FEATURES)
        and required_disabled.issubset(DISABLED_FEATURES)
        and not any("mcp_servers" in argument for argument in cmd)
        and not any(argument in {"--volume", "--mount"} for argument in cmd)
    )
    result = {
        "passed": passed, "image": IMAGE, "image_inspect_id": inspected_id,
        "runtime_source": "../runtime.py", "runtime_source_sha256": hashlib.sha256(SOURCE_RUNTIME.read_bytes()).hexdigest(),
        "runtime_change_from_4c": "none; exact hash-checked frozen module is loaded",
        "disabled_codex_features": list(DISABLED_FEATURES),
        "mcp_servers_configured": False, "host_paths_mounted": False,
        "fresh_container_per_trial": True, "ephemeral_codex_session": True,
        "code_mode_warning_suppressed": False,
        "code_mode_warning_decision": "retained to preserve exact 4C runtime behavior",
        "source_isolation_audit": "../results/isolation-validation.json",
        "same_host_container_isolation": "audited practical boundary, not a cryptographic multi-host guarantee",
    }
    atomic_json(ROOT / "results/isolation-validation.json", result)
    print(json.dumps(result, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

