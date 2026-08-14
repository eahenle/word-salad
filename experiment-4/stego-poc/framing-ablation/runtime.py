#!/usr/bin/env python3
"""Pinned isolated Codex runtime for Experiment 4B.1."""

from __future__ import annotations

import json
import os
import re
import secrets
import signal
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


IMAGE = "sha256:882b506db7abe1d804da2cf4644364ae951accc24f732c04bc7c4ef75b38f254"
MODEL = "gpt-5.6-sol"
EFFORT = "medium"
MARKER_PATTERN = re.compile(rb"^Q4_CANARY_LOG:(\{.*\})\r?$", re.M)
DISABLED_FEATURES = ("shell_snapshot", "shell_tool", "unified_exec", "browser_use",
                     "browser_use_external", "browser_use_full_cdp_access", "computer_use",
                     "apps", "plugins", "remote_plugin", "image_generation", "multi_agent",
                     "multi_agent_v2", "skill_search", "tool_suggest", "auth_elicitation")


def utc_now() -> str: return datetime.now(timezone.utc).isoformat()


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(value); os.replace(temporary, path)


def atomic_json(path: Path, value) -> None:
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def parse_events(raw: bytes) -> dict:
    response = usage = thread_id = None; events = Counter(); items = Counter(); errors = []; non_json = 0
    for line in raw.splitlines():
        if not line.strip(): continue
        try: event = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError): non_json += 1; continue
        kind = str(event.get("type", "unknown")); events[kind] += 1
        if kind == "thread.started": thread_id = event.get("thread_id")
        elif kind == "error" and event.get("message"): errors.append(str(event["message"]))
        elif kind == "item.completed":
            item = event.get("item", {}); item_kind = str(item.get("type", "unknown")); items[item_kind] += 1
            if item_kind == "agent_message": response = item.get("text", "")
        elif kind == "turn.completed": usage = event.get("usage")
    return {"response": response, "usage": usage, "thread_id": thread_id,
            "event_count": sum(events.values()), "event_type_counts": dict(sorted(events.items())),
            "item_type_counts": dict(sorted(items.items())), "non_json_line_count": non_json,
            "error_messages": errors}


def parse_markers(stderr: bytes) -> list[dict]:
    output = []
    for match in MARKER_PATTERN.finditer(stderr):
        try: output.append(json.loads(match.group(1)))
        except (json.JSONDecodeError, UnicodeDecodeError):
            output.append({"parse_error": True, "raw": match.group(1).decode(errors="replace")})
    return output


def command(*, name: str, docker: str = "docker", image: str = IMAGE) -> list[str]:
    base = [docker, "run", "--rm", "--interactive", "--name", name, "--hostname", "subject",
            "--read-only", "--tmpfs", "/subject:rw,nosuid,nodev,size=128m,uid=0,gid=101,mode=770",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m,uid=0,gid=101,mode=1770",
            "--tmpfs", "/codex-home:rw,nosuid,nodev,size=128m,uid=0,gid=0,mode=700",
            "--cap-drop", "ALL", "--cap-add", "SETUID", "--cap-add", "SETGID",
            "--security-opt", "no-new-privileges:true", "--pids-limit", "128", "--memory", "1g",
            "--user", "root", image, "-m", MODEL, "-c", f'model_reasoning_effort="{EFFORT}"',
            "-c", 'mcp_servers.marker.command="/opt/q4/marker_server.py"',
            "-c", "mcp_servers.marker.startup_timeout_sec=10", "--dangerously-bypass-approvals-and-sandbox"]
    for feature in DISABLED_FEATURES: base.extend(("--disable", feature))
    return base + ["-C", "/subject", "exec", "--json", "--ephemeral", "--ignore-user-config",
                   "--ignore-rules", "--strict-config", "--skip-git-repo-check", "-"]


def run_subject(*, prompt: str, auth: Path, timeout: float = 600, docker: str = "docker",
                image: str = IMAGE, name_prefix: str = "word-salad-q4b1") -> dict:
    name = f"{name_prefix}-{secrets.token_hex(6)}"; cmd = command(name=name, docker=docker, image=image)
    auth_bytes = auth.read_bytes(); framed = str(len(auth_bytes)).encode() + b"\n" + auth_bytes + prompt.encode()
    started, began = utc_now(), time.monotonic(); process = None; stdout = stderr = b""
    timed_out = False; exception = None; exit_status = None
    try:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        try: stdout, stderr = process.communicate(framed, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True; subprocess.run([docker, "kill", name], capture_output=True, timeout=30, check=False)
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            stdout, stderr = process.communicate()
        exit_status = process.returncode
    except Exception as exc:
        exception = repr(exc)
        if process is not None and process.poll() is None:
            subprocess.run([docker, "kill", name], capture_output=True, timeout=30, check=False)
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            stdout, stderr = process.communicate(); exit_status = process.returncode
    parsed = parse_events(stdout); error = None
    if timed_out: error = {"type": "timeout", "timeout_seconds": timeout}
    elif exception: error = {"type": "runner_exception", "message": exception}
    elif exit_status != 0: error = {"type": "nonzero_exit", "exit_status": exit_status}
    elif parsed["response"] is None: error = {"type": "missing_final_agent_message"}
    return {"command": cmd, "started_at": started, "finished_at": utc_now(),
            "elapsed_seconds": round(time.monotonic() - began, 3), "exit_status": exit_status,
            "timed_out": timed_out, "error": error, "raw_stdout": stdout, "raw_stderr": stderr,
            "parsed": parsed, "markers": parse_markers(stderr)}
