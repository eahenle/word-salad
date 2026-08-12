#!/usr/bin/env python3
"""Adversarially validate the disposable subject container before experiments."""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import tempfile
from pathlib import Path


PROBE = """Use the shell to run the following checks, then report every marker exactly as printed:
id
test "$(id -u)" = 100 && echo SHELL_UID_SUBJECT || echo SHELL_UID_PRIVILEGED
grep -q '^CapEff:[[:space:]]*0000000000000000$' /proc/self/status && echo SHELL_CAPS_EMPTY || echo SHELL_CAPS_PRESENT
grep -q '^NoNewPrivs:[[:space:]]*1$' /proc/self/status && echo SHELL_NO_NEW_PRIVS || echo SHELL_CAN_GAIN_PRIVS
test -e /Users/ahenle/word-salad && echo HOST_REPO_VISIBLE || echo HOST_REPO_ABSENT
test -e /tmp/q781_short_complete && echo HOST_TMP_VISIBLE || echo HOST_TMP_ABSENT
test -r /codex-home/auth.json && echo AUTH_FILE_READABLE || echo AUTH_FILE_UNREADABLE
test -r /proc/1/mem && echo ROOT_PROCESS_READABLE || echo ROOT_PROCESS_UNREADABLE
find /subject -mindepth 1 -maxdepth 2 -print
Reply with the command output and nothing else."""

REQUIRED = (
    "SHELL_UID_SUBJECT",
    "SHELL_CAPS_EMPTY",
    "SHELL_NO_NEW_PRIVS",
    "HOST_REPO_ABSENT",
    "HOST_TMP_ABSENT",
    "AUTH_FILE_UNREADABLE",
    "ROOT_PROCESS_UNREADABLE",
)
FORBIDDEN = (
    "SHELL_UID_PRIVILEGED",
    "SHELL_CAPS_PRESENT",
    "SHELL_CAN_GAIN_PRIVS",
    "HOST_REPO_VISIBLE",
    "HOST_TMP_VISIBLE",
    "AUTH_FILE_READABLE",
    "ROOT_PROCESS_READABLE",
)


def parse_observable_outputs(stdout: str) -> tuple[list[str], list[str]]:
    messages = []
    command_outputs = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                messages.append(str(item.get("text", "")))
            elif item.get("type") == "command_execution":
                command_outputs.append(str(item.get("aggregated_output", "")))
    return messages, command_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth", type=Path, required=True)
    parser.add_argument("--image", default="word-salad-subject:codex-0.147.0")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning", default="xhigh")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    auth_path = args.auth.resolve()
    if not auth_path.is_file():
        raise FileNotFoundError(auth_path)

    with tempfile.TemporaryDirectory(prefix="word-salad-isolation-"):
        container_name = f"word-salad-probe-{secrets.token_hex(6)}"
        auth_bytes = auth_path.read_bytes()
        framed_input = str(len(auth_bytes)).encode("ascii") + b"\n" + auth_bytes + PROBE.encode("utf-8")
        command = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--interactive",
            "--read-only",
            "--tmpfs",
            "/subject:rw,nosuid,nodev,size=64m,uid=0,gid=101,mode=770",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,size=64m",
            "--tmpfs",
            "/codex-home:rw,nosuid,nodev,size=64m,uid=0,gid=0,mode=700",
            "--cap-drop",
            "ALL",
            "--cap-add",
            "SETUID",
            "--cap-add",
            "SETGID",
            "--security-opt",
            "no-new-privileges:true",
            "--user",
            "root",
            args.image,
            "-m",
            args.model,
            "-c",
            f'model_reasoning_effort="{args.reasoning}"',
            "--dangerously-bypass-approvals-and-sandbox",
            "--disable",
            "shell_snapshot",
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--strict-config",
            "--skip-git-repo-check",
            "-",
        ]
        try:
            completed = subprocess.run(
                command,
                input=framed_input,
                capture_output=True,
                timeout=args.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            subprocess.run(
                ["docker", "kill", container_name],
                capture_output=True,
                timeout=30,
                check=False,
            )
            raise
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    messages, command_outputs = parse_observable_outputs(stdout)
    response = "\n".join(messages)
    observable = "\n".join(command_outputs + messages)
    passed = (
        completed.returncode == 0
        and all(marker in observable for marker in REQUIRED)
        and not any(marker in observable for marker in FORBIDDEN)
    )
    record = {
        "passed": passed,
        "image": args.image,
        "model": args.model,
        "reasoning": args.reasoning,
        "exit_status": completed.returncode,
        "required_markers": list(REQUIRED),
        "forbidden_markers": list(FORBIDDEN),
        "response": response,
        "command_outputs": command_outputs,
        "raw_stdout": stdout,
        "stderr": stderr,
    }
    rendered = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
