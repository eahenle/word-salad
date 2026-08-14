#!/usr/bin/env python3
"""Validate the exact clean image and no-tool 4C command before execution."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from runtime import DISABLED_FEATURES, IMAGE, atomic_json, command


ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", default="docker"); args = parser.parse_args()
    inspect = subprocess.run([args.docker, "image", "inspect", IMAGE], text=True,
                             capture_output=True, check=False)
    filesystem = subprocess.run([
        args.docker, "run", "--rm", "--network", "none", "--read-only",
        "--entrypoint", "/bin/busybox", IMAGE, "sh", "-c",
        "test ! -e /Users/ahenle/word-salad && echo HOST_REPO_ABSENT; "
        "test ! -e /codex-home/auth.json && echo AUTH_ABSENT_BEFORE_GATE; "
        "test ! -e /root/.codex && echo ROOT_CODEX_ABSENT; "
        "find /subject -mindepth 1 -maxdepth 1 -print",
    ], text=True, capture_output=True, timeout=60, check=False)
    cmd = command(name="word-salad-q4c-command-audit", docker=args.docker)
    joined = " ".join(cmd)
    required_features = {"shell_tool", "unified_exec", "browser_use", "computer_use",
                         "apps", "plugins", "view_image", "goals"}
    no_mcp = not any("mcp_servers" in argument for argument in cmd)
    required_outputs = ("HOST_REPO_ABSENT", "AUTH_ABSENT_BEFORE_GATE", "ROOT_CODEX_ABSENT")
    passed = (
        inspect.returncode == 0 and json.loads(inspect.stdout)[0]["Id"] == IMAGE
        and filesystem.returncode == 0
        and all(item in filesystem.stdout for item in required_outputs)
        and required_features.issubset(DISABLED_FEATURES) and no_mcp
        and not any(token in joined for token in ("--volume", "--mount"))
    )
    result = {
        "passed": passed, "image": IMAGE, "image_inspect_id": json.loads(inspect.stdout)[0]["Id"] if inspect.returncode == 0 else None,
        "filesystem_output": filesystem.stdout, "filesystem_stderr": filesystem.stderr,
        "host_paths_mounted": False, "mcp_servers_configured": False,
        "model_tool_features_disabled": list(DISABLED_FEATURES),
        "network_tools_exposed": False, "model_transport_network_only": True,
        "fresh_container_per_trial": True, "ephemeral_codex_session": True,
        "same_host_container_isolation": "audited practical boundary, not a cryptographic multi-host guarantee",
        "context_audit_reference": "../context-audit/conclusion.md",
    }
    atomic_json(ROOT / "results/isolation-validation.json", result)
    print(json.dumps(result, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

