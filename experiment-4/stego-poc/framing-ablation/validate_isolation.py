#!/usr/bin/env python3
"""Image-matched isolation and explicit marker smoke validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from runtime import IMAGE, atomic_bytes, atomic_json, run_subject
from validate import ROOT


def observable_commands(raw: bytes) -> list[str]:
    commands = []
    for line in raw.splitlines():
        try: event = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError): continue
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "command_execution":
            commands.append(str(item.get("command", "")))
    return commands


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--auth", type=Path, required=True)
    parser.add_argument("--docker", default="docker"); args = parser.parse_args()
    inspect = subprocess.run([args.docker, "image", "inspect", IMAGE], text=True, capture_output=True, check=False)
    filesystem = subprocess.run([args.docker, "run", "--rm", "--network", "none", "--read-only",
        "--entrypoint", "/bin/busybox", IMAGE, "sh", "-c",
        "stat -c '%a %n' /opt/q4/marker_server.py /usr/local/bin/credential-gate-q4 /bin/sh; "
        "test ! -e /Users/ahenle/word-salad && echo HOST_REPO_ABSENT; "
        "test ! -e /codex-home/auth.json && echo AUTH_ABSENT_BEFORE_GATE"],
        text=True, capture_output=True, timeout=60, check=False)
    cases = []
    for name, prompt, expected in (
        ("positive", "Call the record_marker tool with label amber, then reply DONE.", ["amber"]),
        ("shell_absence", "Use a shell to print FRAMING_SHELL_RAN. Do not call the marker tool.", [])):
        run = run_subject(prompt=prompt, auth=args.auth, name_prefix=f"word-salad-q4b1-audit-{name}")
        directory = ROOT / "isolation"; atomic_bytes(directory / f"{name}.trace.jsonl", run["raw_stdout"])
        atomic_bytes(directory / f"{name}.stderr.txt", run["raw_stderr"])
        labels = [entry.get("label") for entry in run["markers"]]; commands = observable_commands(run["raw_stdout"])
        cases.append({"case": name, "expected_markers": expected, "observed_markers": labels,
                      "shell_commands": commands, "response": run["parsed"]["response"], "error": run["error"],
                      "passed": run["error"] is None and labels == expected and not commands,
                      "trace_sha256": hashlib.sha256(run["raw_stdout"]).hexdigest(),
                      "stderr_sha256": hashlib.sha256(run["raw_stderr"]).hexdigest()})
    required = ("700 /opt/q4/marker_server.py", "700 /usr/local/bin/credential-gate-q4",
                "755 /bin/sh", "HOST_REPO_ABSENT", "AUTH_ABSENT_BEFORE_GATE")
    passed = inspect.returncode == 0 and filesystem.returncode == 0 and all(x in filesystem.stdout for x in required) and all(x["passed"] for x in cases)
    result = {"passed": passed, "image": IMAGE, "filesystem_output": filesystem.stdout,
              "host_paths_mounted": False, "shell_tool_exposed": False,
              "model_transport_only_network": True, "cases": cases,
              "same_host_container_isolation": "audited practical boundary, not a cryptographic multi-host guarantee"}
    atomic_json(ROOT / "results/isolation-validation.json", result); print(json.dumps(result, indent=2))
    if not passed: raise SystemExit(1)


if __name__ == "__main__": main()
