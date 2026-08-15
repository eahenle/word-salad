#!/usr/bin/env python3
"""Validate the exact audited image and frozen no-tool subject command."""

from __future__ import annotations

import argparse
import json
import subprocess

from generate_clean import ROOT
from runtime import DISABLED_FEATURES, IMAGE, atomic_json, command


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", default="docker")
    args = parser.parse_args()
    inspect = subprocess.run(
        [args.docker, "image", "inspect", IMAGE], text=True, capture_output=True, check=False
    )
    filesystem = subprocess.run([
        args.docker, "run", "--rm", "--network", "none", "--read-only",
        "--entrypoint", "/bin/busybox", IMAGE, "sh", "-c",
        "test ! -e /Users/ahenle/word-salad && echo HOST_REPO_ABSENT; "
        "test ! -e /codex-home/auth.json && echo AUTH_ABSENT_BEFORE_GATE; "
        "test ! -e /root/.codex && echo ROOT_CODEX_ABSENT; "
        "find /subject -mindepth 1 -maxdepth 1 -print",
    ], text=True, capture_output=True, timeout=60, check=False)
    cmd = command(name="word-salad-q6-command-audit", docker=args.docker)
    joined = " ".join(cmd)
    required = {
        "shell_tool", "unified_exec", "browser_use", "computer_use", "apps",
        "plugins", "view_image", "goals",
    }
    outputs = ("HOST_REPO_ABSENT", "AUTH_ABSENT_BEFORE_GATE", "ROOT_CODEX_ABSENT")
    inspected_id = json.loads(inspect.stdout)[0]["Id"] if inspect.returncode == 0 else None
    passed = (
        inspect.returncode == 0
        and inspected_id == IMAGE
        and filesystem.returncode == 0
        and all(value in filesystem.stdout for value in outputs)
        and required.issubset(DISABLED_FEATURES)
        and not any(token in joined for token in ("--volume", "--mount", "mcp_servers"))
    )
    result = {
        "passed": passed,
        "image": IMAGE,
        "image_inspect_id": inspected_id,
        "filesystem_output": filesystem.stdout,
        "filesystem_stderr": filesystem.stderr,
        "host_paths_mounted": False,
        "mcp_servers_configured": False,
        "model_tool_features_disabled": list(DISABLED_FEATURES),
        "fresh_container_per_trial": True,
        "ephemeral_codex_session": True,
        "same_host_container_isolation": "audited practical boundary, not a cryptographic multi-host guarantee",
        "context_audit_reference": "../../experiment-4/context-audit/conclusion.md",
    }
    atomic_json(ROOT / "results/isolation-validation.json", result)
    print(json.dumps(result, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
