#!/usr/bin/env python3
"""Pinned Docker/Codex runtime primitives shared by Experiment 3 runners."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import signal
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


IMAGE = "sha256:883e4d8d659d28c25d2473c0dec9ff43d1bafb7ce3920ada270627df3c202402"
MODELS = (
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.3-codex-spark",
)
EFFORTS = ("medium", "high", "xhigh")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def atomic_json(path: Path, value: dict) -> None:
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def cell_slug(model: str, effort: str) -> str:
    return model.replace(".", "_") + "__" + effort


def parse_events(raw: bytes) -> dict:
    response = None
    usage = None
    thread_id = None
    events: Counter[str] = Counter()
    items: Counter[str] = Counter()
    non_json = 0
    error_messages = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            non_json += 1
            continue
        kind = str(event.get("type", "unknown"))
        events[kind] += 1
        if kind == "error" and event.get("message"):
            error_messages.append(str(event["message"]))
        elif kind == "turn.failed" and isinstance(event.get("error"), dict):
            if event["error"].get("message"):
                error_messages.append(str(event["error"]["message"]))
        if kind == "thread.started":
            thread_id = event.get("thread_id")
        elif kind == "item.completed":
            item = event.get("item", {})
            item_kind = str(item.get("type", "unknown"))
            items[item_kind] += 1
            if item_kind == "agent_message":
                response = item.get("text", "")
        elif kind == "turn.completed":
            usage = event.get("usage")
    return {
        "response": response,
        "usage": usage,
        "thread_id": thread_id,
        "event_count": sum(events.values()),
        "event_type_counts": dict(sorted(events.items())),
        "item_type_counts": dict(sorted(items.items())),
        "non_json_line_count": non_json,
        "error_messages": error_messages,
    }


def container_command(
    *, docker: str, image: str, model: str, effort: str, name: str,
) -> list[str]:
    if model not in MODELS or effort not in EFFORTS:
        raise ValueError("exact requested model/reasoning cell required")
    return [
        docker,
        "run",
        "--rm",
        "--interactive",
        "--name",
        name,
        "--hostname",
        "subject",
        "--read-only",
        "--tmpfs",
        "/subject:rw,nosuid,nodev,size=256m,uid=0,gid=101,mode=770",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=256m,uid=0,gid=101,mode=1770",
        "--tmpfs",
        "/codex-home:rw,nosuid,nodev,size=128m,uid=0,gid=0,mode=700",
        "--cap-drop",
        "ALL",
        "--cap-add",
        "SETUID",
        "--cap-add",
        "SETGID",
        "--security-opt",
        "no-new-privileges:true",
        "--pids-limit",
        "256",
        "--memory",
        "2g",
        "--user",
        "root",
        image,
        "-m",
        model,
        "-c",
        f'model_reasoning_effort="{effort}"',
        "--dangerously-bypass-approvals-and-sandbox",
        "--disable",
        "shell_snapshot",
        "-C",
        "/subject",
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--strict-config",
        "--skip-git-repo-check",
        "-",
    ]


def run_subject(
    *, prompt: str, auth: Path, model: str, effort: str, timeout: float,
    docker: str = "docker", image: str = IMAGE, name_prefix: str = "word-salad-q3",
) -> dict:
    name = f"{name_prefix}-{secrets.token_hex(6)}"
    command = container_command(
        docker=docker, image=image, model=model, effort=effort, name=name
    )
    auth_bytes = auth.read_bytes()
    framed = str(len(auth_bytes)).encode("ascii") + b"\n" + auth_bytes + prompt.encode("utf-8")
    started = utc_now()
    began = time.monotonic()
    raw_stdout = b""
    raw_stderr = b""
    timed_out = False
    exception = None
    exit_status = None
    process = None
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            raw_stdout, raw_stderr = process.communicate(framed, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            subprocess.run([docker, "kill", name], capture_output=True, timeout=30, check=False)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            raw_stdout, raw_stderr = process.communicate()
        exit_status = process.returncode
    except Exception as exc:
        exception = repr(exc)
        if process is not None and process.poll() is None:
            subprocess.run([docker, "kill", name], capture_output=True, timeout=30, check=False)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            extra_out, extra_err = process.communicate()
            raw_stdout += extra_out or b""
            raw_stderr += extra_err or b""
            exit_status = process.returncode
    elapsed = round(time.monotonic() - began, 3)
    parsed = parse_events(raw_stdout)
    error = None
    if timed_out:
        error = {"type": "timeout", "timeout_seconds": timeout}
    elif exception:
        error = {"type": "runner_exception", "message": exception}
    elif exit_status != 0:
        combined = "\n".join(parsed["error_messages"]) + "\n" + raw_stderr.decode(
            "utf-8", errors="replace"
        )
        lowered = combined.lower()
        if "usage limit" in lowered:
            kind = "usage_cap"
        elif "capacity" in lowered or "temporarily unavailable" in lowered:
            kind = "temporary_capacity"
        else:
            kind = "nonzero_exit"
        error = {"type": kind, "exit_status": exit_status}
    elif parsed["response"] is None:
        error = {"type": "missing_final_agent_message"}
    return {
        "command": command,
        "started_at": started,
        "finished_at": utc_now(),
        "elapsed_seconds": elapsed,
        "exit_status": exit_status,
        "timed_out": timed_out,
        "error": error,
        "raw_stdout": raw_stdout,
        "raw_stderr": raw_stderr,
        "parsed": parsed,
    }
