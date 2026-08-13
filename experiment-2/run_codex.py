#!/usr/bin/env python3
"""Run fresh hardened Codex subjects for Experiment 2 with full trace capture."""

from __future__ import annotations

import argparse
import concurrent.futures
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
from typing import Sequence

from generate import ARMS, Task, build_tasks
from validate import validate


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


def command(args: argparse.Namespace, name: str) -> list[str]:
    return [
        args.docker,
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
        args.image,
        "-m",
        args.model,
        "-c",
        f'model_reasoning_effort="{args.reasoning}"',
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


def run_one(task: Task, args: argparse.Namespace, root: Path) -> tuple[int, dict]:
    numeric_id = int(task.neutral_id[1:])
    paths = {
        "attempt": root / "attempts" / f"{task.neutral_id}.json",
        "completed": root / "completed" / f"{task.neutral_id}.json",
        "trace": root / "traces" / f"{task.neutral_id}.jsonl",
        "stderr": root / "stderr" / f"{task.neutral_id}.txt",
    }
    if paths["completed"].exists():
        return numeric_id, json.loads(paths["completed"].read_text(encoding="utf-8"))
    if paths["attempt"].exists():
        raise RuntimeError(f"{task.neutral_id} has an orphaned/active attempt; no implicit retry")
    paths["attempt"].parent.mkdir(parents=True, exist_ok=True)
    name = f"word-salad-{task.neutral_id}-{secrets.token_hex(6)}"
    cmd = command(args, name)
    auth = args.auth.read_bytes()
    framed = str(len(auth)).encode("ascii") + b"\n" + auth + task.prompt.encode("utf-8")
    started = utc_now()
    began = time.monotonic()
    attempt = {
        "neutral_id": task.neutral_id,
        "started_at": started,
        "command": cmd,
        "container_image": args.image,
        "prompt_sha256": task.metadata["prompt_sha256"],
    }
    with paths["attempt"].open("x", encoding="utf-8") as handle:
        json.dump(attempt, handle, indent=2)
        handle.write("\n")
    raw_stdout = b""
    raw_stderr = b""
    timed_out = False
    exception = None
    process = None
    exit_status = None
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            raw_stdout, raw_stderr = process.communicate(framed, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            subprocess.run(
                [args.docker, "kill", name], capture_output=True, timeout=30, check=False
            )
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            raw_stdout, raw_stderr = process.communicate()
        exit_status = process.returncode
    except Exception as exc:
        exception = repr(exc)
        if process is not None and process.poll() is None:
            subprocess.run(
                [args.docker, "kill", name], capture_output=True, timeout=30, check=False
            )
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            extra_out, extra_err = process.communicate()
            raw_stdout += extra_out or b""
            raw_stderr += extra_err or b""
            exit_status = process.returncode
    elapsed = time.monotonic() - began
    atomic_bytes(paths["trace"], raw_stdout)
    atomic_bytes(paths["stderr"], raw_stderr)
    parsed = parse_events(raw_stdout)
    error = None
    if timed_out:
        error = {"type": "timeout", "timeout_seconds": args.timeout}
    elif exception:
        error = {"type": "runner_exception", "message": exception}
    elif exit_status != 0:
        error_type = (
            "usage_cap"
            if any("usage limit" in message.lower() for message in parsed["error_messages"])
            else "nonzero_exit"
        )
        error = {"type": error_type, "exit_status": exit_status}
    elif parsed["response"] is None:
        error = {"type": "missing_final_agent_message"}
    record = {
        "trial_id": task.trial_id,
        "neutral_id": task.neutral_id,
        "arm": task.arm,
        "condition": task.condition,
        "payload_identity": task.payload_identity,
        "answer_identity": task.metadata["answer_identity"],
        "lanes": task.lanes,
        "seed": task.seed,
        "signal_phase": task.metadata["signal_phase"],
        "model": args.model,
        "reasoning": args.reasoning,
        "prompt_words": task.metadata["prompt_words"],
        "prompt_sha256": task.metadata["prompt_sha256"],
        "prompt_file": f"prompts/{task.arm}/{task.neutral_id}.txt",
        "trace_file": f"traces/{task.neutral_id}.jsonl",
        "stderr_file": f"stderr/{task.neutral_id}.txt",
        "response": parsed["response"] or "",
        "runner": {
            "method": "codex_exec_ephemeral_container_full_trace",
            "container_image": args.image,
            "started_at": started,
            "finished_at": utc_now(),
            "thread_id": parsed["thread_id"],
            "aggregate_usage": parsed["usage"],
            "elapsed_seconds": round(elapsed, 3),
            "exit_status": exit_status,
            "timed_out": timed_out,
            "error": error,
            "trace_bytes": len(raw_stdout),
            "trace_sha256": sha256_bytes(raw_stdout),
            "stderr_bytes": len(raw_stderr),
            "stderr_sha256": sha256_bytes(raw_stderr),
            "event_count": parsed["event_count"],
            "event_type_counts": parsed["event_type_counts"],
            "item_type_counts": parsed["item_type_counts"],
            "non_json_line_count": parsed["non_json_line_count"],
            "error_messages": parsed["error_messages"],
        },
    }
    atomic_json(paths["completed"], record)
    return numeric_id, record


def finalize(
    root: Path,
    tasks: Sequence[Task],
    args: argparse.Namespace,
    *,
    record_invocation: bool = True,
) -> None:
    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "completed").glob("r*.json"))
    ]
    results = root / "results"
    results.mkdir(parents=True, exist_ok=True)
    atomic_bytes(
        results / "trials-unscored.jsonl",
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records).encode(),
    )
    completed = {record["neutral_id"] for record in records}
    metadata = [task.metadata for task in tasks if task.neutral_id in completed]
    atomic_bytes(
        results / "metadata.jsonl",
        "".join(json.dumps(record) + "\n" for record in metadata).encode(),
    )
    previous = json.loads((results / "manifest.json").read_text()) if (results / "manifest.json").exists() else {}
    invocations = previous.get("run_invocations", [])
    if record_invocation:
        invocations = invocations + [
            {"finished_at": utc_now(), "requested_trial_ids": args.trial_ids}
        ]
    manifest = {
        "experiment": "Experiment 2 paired equal-multiset A/B",
        "model": args.model,
        "reasoning": args.reasoning,
        "container_image": args.image,
        "worker_count": args.workers,
        "timeout_seconds": args.timeout,
        "scheduled_trials": len(tasks),
        "completed_trials": len(records),
        "completed_by_arm": dict(sorted(Counter(r["arm"] for r in records).items())),
        "completed_by_condition": dict(sorted(Counter(r["condition"] for r in records).items())),
        "errored_or_nonresponse_trials": sum(r["runner"]["error"] is not None for r in records),
        "full_stdout_jsonl_preserved": True,
        "answer_keys_stored_in_subject_metadata": False,
        "run_invocations": invocations,
    }
    atomic_json(results / "manifest.json", manifest)


def select(tasks: Sequence[Task], args: argparse.Namespace) -> list[Task]:
    selected = list(tasks)
    if args.arms:
        selected = [task for task in selected if task.arm in args.arms]
    if args.conditions:
        selected = [task for task in selected if task.condition in args.conditions]
    if args.payload_identities:
        selected = [
            task for task in selected if (task.payload_identity or "none") in args.payload_identities
        ]
    if args.lanes:
        selected = [task for task in selected if task.lanes in args.lanes]
    if args.seeds:
        selected = [task for task in selected if task.seed in args.seeds]
    if args.trial_ids:
        wanted = set(args.trial_ids)
        available = {task.neutral_id for task in tasks}
        if wanted - available:
            raise ValueError(f"unknown IDs: {sorted(wanted - available)}")
        selected = [task for task in selected if task.neutral_id in wanted]
        if len(selected) != len(wanted):
            raise ValueError("trial IDs conflict with other selectors")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--auth", type=Path, required=True)
    parser.add_argument("--isolation-validation", type=Path, required=True)
    parser.add_argument("--image", default="sha256:883e4d8d659d28c25d2473c0dec9ff43d1bafb7ce3920ada270627df3c202402")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning", default="xhigh")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--arms", nargs="+", choices=ARMS)
    parser.add_argument("--conditions", nargs="+", choices=("clean", "signal", "all_shuffled"))
    parser.add_argument("--payload-identities", nargs="+", choices=("A", "B", "none"))
    parser.add_argument("--lanes", nargs="+", type=int, choices=(1, 2, 4))
    parser.add_argument("--seeds", nargs="+", type=int, choices=range(1, 21))
    parser.add_argument("--trial-ids", nargs="+")
    parser.add_argument(
        "--finalize-only",
        action="store_true",
        help="rebuild aggregate result files from completed records without running subjects",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if not args.auth.is_file():
        raise FileNotFoundError(args.auth)
    isolation = json.loads(args.isolation_validation.read_text(encoding="utf-8"))
    if not isolation.get("passed") or isolation.get("image") != args.image:
        raise RuntimeError("isolation validation missing, failed, or image-mismatched")
    validate(root)
    tasks = build_tasks(root)
    if args.finalize_only:
        finalize(root, tasks, args, record_invocation=False)
        print(f"finalized {len(list((root / 'completed').glob('r*.json')))}/{len(tasks)} Experiment 2 records")
        return
    requested = select(tasks, args)
    pending = []
    for task in requested:
        attempt = root / "attempts" / f"{task.neutral_id}.json"
        completed = root / "completed" / f"{task.neutral_id}.json"
        if completed.exists():
            continue
        if attempt.exists():
            raise RuntimeError(f"{task.neutral_id} has an orphaned attempt; no implicit retry")
        pending.append(task)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run_one, task, args, root) for task in pending]
        for count, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            _, record = future.result()
            status = "ok" if record["runner"]["error"] is None else "error"
            print(f"{count}/{len(pending)} {record['neutral_id']} {status}", flush=True)
            error = record["runner"].get("error") or {}
            if error.get("type") == "usage_cap":
                for queued in futures:
                    queued.cancel()
                raise RuntimeError(
                    f"usage cap detected in {record['neutral_id']}; queue halted for explicit archival"
                )
    finalize(root, tasks, args)
    print(f"finalized {len(list((root / 'completed').glob('r*.json')))}/{len(tasks)} Experiment 2 records")


if __name__ == "__main__":
    main()
