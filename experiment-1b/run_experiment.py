#!/usr/bin/env python3
"""Run fresh blind Codex subjects while preserving complete observable traces."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import secrets
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from generate import (
    EXPERIMENT_GENERATOR_VERSION,
    GENERATOR_VERSION,
    VARIANT_ORDER,
    GeneratedTask,
    build_tasks,
)
from normalize import NORMALIZATION_VERSION
from validate import BASELINE_SHA, BASELINE_TAG, validate


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _manifest_argv(argv: Sequence[str]) -> list[str]:
    """Preserve invocation shape without persisting the host credential path."""
    redacted = list(argv)
    for index, argument in enumerate(redacted[:-1]):
        if argument == "--auth":
            redacted[index + 1] = "AUTH_JSON"
    return redacted


def _atomic_write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def _atomic_write_json(path: Path, value: dict) -> None:
    _atomic_write_bytes(
        path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


def _git_value(root: Path, *arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def _codex_version(args: argparse.Namespace) -> str | None:
    if args.runtime == "container":
        command = [
            args.docker,
            "run",
            "--rm",
            "--entrypoint",
            "codex",
            args.image,
            "--version",
        ]
    else:
        command = [args.codex, "--version"]
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip().rsplit(maxsplit=1)[-1]


def _parse_events(raw_stdout: bytes) -> dict:
    response = None
    usage = None
    thread_id = None
    event_types: Counter[str] = Counter()
    item_types: Counter[str] = Counter()
    parse_failures = 0
    event_count = 0
    for raw_line in raw_stdout.splitlines():
        if not raw_line.strip():
            continue
        try:
            event = json.loads(raw_line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            parse_failures += 1
            continue
        event_count += 1
        event_type = str(event.get("type", "unknown"))
        event_types[event_type] += 1
        if event_type == "thread.started":
            thread_id = event.get("thread_id")
        elif event_type == "item.completed":
            item = event.get("item", {})
            item_type = str(item.get("type", "unknown"))
            item_types[item_type] += 1
            if item_type == "agent_message":
                response = item.get("text", "")
        elif event_type == "turn.completed":
            usage = event.get("usage")
    return {
        "final_response": response,
        "aggregate_usage": usage,
        "thread_id": thread_id,
        "event_count": event_count,
        "event_type_counts": dict(sorted(event_types.items())),
        "item_type_counts": dict(sorted(item_types.items())),
        "non_json_line_count": parse_failures,
    }


def _command(
    args: argparse.Namespace, cwd: Path, container_name: str = "NEUTRAL_CONTAINER"
) -> list[str]:
    if args.runtime == "container":
        return [
            args.docker,
            "run",
            "--rm",
            "--interactive",
            "--name",
            container_name,
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
    return [
        args.codex,
        "-m",
        args.model,
        "-c",
        f'model_reasoning_effort="{args.reasoning}"',
        "-s",
        "read-only",
        "-a",
        "never",
        "-C",
        str(cwd),
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--strict-config",
        "--skip-git-repo-check",
        "-",
    ]


def _run_subject(
    task: GeneratedTask, args: argparse.Namespace, root: Path
) -> tuple[int, dict]:
    numeric_id = int(task.neutral_id[1:])
    attempt_path = root / "attempts" / f"{task.neutral_id}.json"
    completed_path = root / "completed" / f"{task.neutral_id}.json"
    trace_path = root / "traces" / f"{task.neutral_id}.jsonl"
    stderr_path = root / "stderr" / f"{task.neutral_id}.txt"
    if completed_path.exists():
        return numeric_id, json.loads(completed_path.read_text(encoding="utf-8"))
    attempt_path.parent.mkdir(parents=True, exist_ok=True)
    if attempt_path.exists():
        raise RuntimeError(
            f"orphaned or active attempt exists for {task.neutral_id}; no implicit retry"
        )

    started_wall = utc_now()
    started_monotonic = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="q.") as subject_cwd_name:
        subject_cwd = Path(subject_cwd_name)
        container_name = f"word-salad-{task.neutral_id}-{secrets.token_hex(6)}"
        command = _command(args, subject_cwd, container_name)
        if args.runtime == "container":
            auth_bytes = args.auth.read_bytes()
            process_input = (
                str(len(auth_bytes)).encode("ascii")
                + b"\n"
                + auth_bytes
                + task.prompt.encode("utf-8")
            )
        else:
            process_input = task.prompt.encode("utf-8")
        attempt = {
            "neutral_id": task.neutral_id,
            "started_at": started_wall,
            "command": command,
            "runtime": args.runtime,
            "container_image": args.image if args.runtime == "container" else None,
            "subject_cwd_basename": subject_cwd.name,
            "inherited_environment_variable_names": sorted(os.environ),
            "prompt_sha256": task.metadata["prompt_sha256"],
        }
        with attempt_path.open("x", encoding="utf-8") as handle:
            json.dump(attempt, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

        timed_out = False
        infrastructure_exception = None
        process = None
        raw_stdout = b""
        raw_stderr = b""
        exit_status = None
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                raw_stdout, raw_stderr = process.communicate(
                    process_input, timeout=args.timeout
                )
            except subprocess.TimeoutExpired:
                timed_out = True
                if args.runtime == "container":
                    subprocess.run(
                        [args.docker, "kill", container_name],
                        text=True,
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                raw_stdout, raw_stderr = process.communicate()
            exit_status = process.returncode
        except Exception as exc:  # preserve unexpected runner failures as data
            infrastructure_exception = repr(exc)
            if process is not None and process.poll() is None:
                if args.runtime == "container":
                    subprocess.run(
                        [args.docker, "kill", container_name],
                        text=True,
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                extra_stdout, extra_stderr = process.communicate()
                raw_stdout += extra_stdout or b""
                raw_stderr += extra_stderr or b""
                exit_status = process.returncode

    elapsed = time.monotonic() - started_monotonic
    _atomic_write_bytes(trace_path, raw_stdout)
    _atomic_write_bytes(stderr_path, raw_stderr)
    parsed = _parse_events(raw_stdout)
    final_response = parsed.pop("final_response")
    error = None
    if timed_out:
        error = {"type": "timeout", "timeout_seconds": args.timeout}
    elif infrastructure_exception is not None:
        error = {"type": "runner_exception", "message": infrastructure_exception}
    elif exit_status != 0:
        error = {"type": "nonzero_exit", "exit_status": exit_status}
    elif final_response is None:
        error = {"type": "missing_final_agent_message"}

    record = {
        "trial_id": task.trial_id,
        "neutral_id": task.neutral_id,
        "variant": task.variant,
        "condition": task.condition,
        "lanes": task.lanes,
        "seed": task.seed,
        "signal_phase": task.metadata["signal_phase"],
        "model": args.model,
        "reasoning": args.reasoning,
        "prompt_words": task.metadata["prompt_words"],
        "prompt_sha256": task.metadata["prompt_sha256"],
        "prompt_file": f"prompts/{task.variant}/{task.neutral_id}.txt",
        "trace_file": f"traces/{task.neutral_id}.jsonl",
        "stderr_file": f"stderr/{task.neutral_id}.txt",
        "response": final_response or "",
        "exact_success": None,
        "semantic_success": None,
        "correct_assignment_count": None,
        "malformed_object_substitutions": None,
        "encoding_discovered": None,
        "classification": None,
        "strategy": None,
        "notes": "",
        "runner": {
            "method": (
                "codex_exec_ephemeral_container_full_trace"
                if args.runtime == "container"
                else "codex_exec_ephemeral_full_trace"
            ),
            "runtime": args.runtime,
            "container_image": args.image if args.runtime == "container" else None,
            "started_at": started_wall,
            "finished_at": utc_now(),
            "thread_id": parsed["thread_id"],
            "aggregate_usage": parsed["aggregate_usage"],
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
        },
    }
    _atomic_write_json(completed_path, record)
    return numeric_id, record


def _load_completed(root: Path) -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "completed").glob("q*.json"))
    ]


def _finalize_results(root: Path, all_tasks: Sequence[GeneratedTask]) -> None:
    records = _load_completed(root)
    results = root / "results"
    results.mkdir(parents=True, exist_ok=True)
    trials_text = "".join(
        json.dumps(record, ensure_ascii=False) + "\n" for record in records
    )
    _atomic_write_bytes(results / "trials-unscored.jsonl", trials_text.encode("utf-8"))
    completed_ids = {record["neutral_id"] for record in records}
    metadata_text = "".join(
        json.dumps(task.metadata, ensure_ascii=False) + "\n"
        for task in all_tasks
        if task.neutral_id in completed_ids
    )
    _atomic_write_bytes(results / "metadata.jsonl", metadata_text.encode("utf-8"))


def _manifest(
    *,
    root: Path,
    repo_root: Path,
    args: argparse.Namespace,
    invocation_started: str,
    invocation_finished: str,
    requested: Sequence[GeneratedTask],
    all_tasks: Sequence[GeneratedTask],
) -> None:
    path = root / "results" / "manifest.json"
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    history = previous.get("run_invocations", [])
    history.append(
        {
            "started_at": invocation_started,
            "finished_at": invocation_finished,
            "argv": _manifest_argv(sys.argv),
            "variants": args.variants,
            "tasks_requested": len(requested),
            "workers": args.workers,
            "timeout_seconds": args.timeout,
            "runtime": args.runtime,
            "container_image": args.image if args.runtime == "container" else None,
        }
    )
    completed = _load_completed(root)
    completed_by_variant = Counter(record["variant"] for record in completed)
    errors = sum(record["runner"]["error"] is not None for record in completed)
    tag_target = _git_value(repo_root, "rev-list", "-n", "1", BASELINE_TAG)
    manifest = {
        "experiment": "Experiment 1A-R and 1B surface-normalization matrix",
        "baseline_commit": BASELINE_SHA,
        "baseline_tag": BASELINE_TAG,
        "baseline_tag_target": tag_target,
        "git_commit_at_execution": _git_value(repo_root, "rev-parse", "HEAD"),
        "git_worktree_status_at_finalization": _git_value(repo_root, "status", "--short"),
        "model": args.model,
        "reasoning": args.reasoning,
        "codex_cli_version": _codex_version(args),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "generator_version": GENERATOR_VERSION,
        "experiment_generator_version": EXPERIMENT_GENERATOR_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "payload_sha256": all_tasks[0].metadata["source_payload_sha256"],
        "variants": list(VARIANT_ORDER),
        "conditions": ["signal", "all_shuffled"],
        "lane_counts": [1, 2, 4, 8],
        "seeds": list(range(1, 11)),
        "scheduled_trials": len(all_tasks),
        "completed_trials": len(completed),
        "completed_by_variant": dict(sorted(completed_by_variant.items())),
        "errored_or_nonresponse_trials": errors,
        "workers": args.workers,
        "timeout_seconds": args.timeout,
        "runtime": args.runtime,
        "container_image": args.image if args.runtime == "container" else None,
        "isolation_validation_file": (
            str(args.isolation_validation) if args.runtime == "container" else None
        ),
        "authentication_delivery": (
            "length_prefixed_stdin_to_root_only_tmpfs"
            if args.runtime == "container"
            else "host_profile"
        ),
        "command_template": _command(args, Path("EMPTY_NEUTRAL_TEMP_DIR")),
        "full_stdout_jsonl_preserved": True,
        "stderr_preserved": True,
        "answer_key_stored_in_source": False,
        "run_invocations": history,
    }
    _atomic_write_json(path, manifest)


def _check_state(root: Path, requested: Sequence[GeneratedTask]) -> list[GeneratedTask]:
    pending = []
    for task in requested:
        attempt = root / "attempts" / f"{task.neutral_id}.json"
        completed = root / "completed" / f"{task.neutral_id}.json"
        if completed.exists():
            continue
        if attempt.exists():
            raise RuntimeError(
                f"{task.neutral_id} has an attempt record but no completion; "
                "the protocol forbids an implicit retry"
            )
        pending.append(task)
    return pending


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--historical-root", type=Path, default=root.parent / "multiplex-experiment")
    parser.add_argument("--payload", type=Path, default=root / "payload.txt")
    parser.add_argument(
        "--variants", nargs="+", choices=VARIANT_ORDER, default=list(VARIANT_ORDER)
    )
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning", default="xhigh")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--runtime", choices=("local", "container"), default="local")
    parser.add_argument("--docker", default="docker")
    parser.add_argument(
        "--image",
        default="sha256:883e4d8d659d28c25d2473c0dec9ff43d1bafb7ce3920ada270627df3c202402",
    )
    parser.add_argument("--auth", type=Path)
    parser.add_argument("--isolation-validation", type=Path)
    parser.add_argument("--trial-ids", nargs="+")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.workers < 1:
        raise ValueError("workers must be positive")
    root = args.root.resolve()
    repo_root = root.parent
    if args.runtime == "container":
        if args.auth is None or not args.auth.is_file():
            raise FileNotFoundError("container runtime requires --auth pointing to auth.json")
        if args.isolation_validation is None or not args.isolation_validation.is_file():
            raise FileNotFoundError(
                "container runtime requires --isolation-validation from a passed probe"
            )
        isolation = json.loads(args.isolation_validation.read_text(encoding="utf-8"))
        if not isolation.get("passed"):
            raise RuntimeError("isolation validation did not pass")
        if isolation.get("image") != args.image:
            raise RuntimeError(
                "isolation validation image does not match requested container image"
            )
    payload = args.payload.read_text(encoding="utf-8").strip()
    tag_target = _git_value(repo_root, "rev-list", "-n", "1", BASELINE_TAG)
    if tag_target != BASELINE_SHA:
        raise RuntimeError(
            f"baseline tag {BASELINE_TAG} resolves to {tag_target!r}, expected {BASELINE_SHA}"
        )
    validate(
        root=root,
        historical_root=args.historical_root.resolve(),
        payload=payload,
        variants=list(args.variants),
    )
    all_tasks = build_tasks(payload, VARIANT_ORDER)
    requested = [task for task in all_tasks if task.variant in args.variants]
    if args.trial_ids:
        requested_ids = set(args.trial_ids)
        all_ids = {task.neutral_id for task in all_tasks}
        unknown_ids = requested_ids - all_ids
        if unknown_ids:
            raise ValueError(f"unknown trial IDs: {sorted(unknown_ids)}")
        requested = [task for task in requested if task.neutral_id in requested_ids]
        if len(requested) != len(requested_ids):
            raise ValueError("--trial-ids includes IDs outside the requested variants")
    pending = _check_state(root, requested)
    invocation_started = utc_now()
    if not pending:
        print("all requested trials already have completion records")
    else:
        records: dict[int, dict] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_run_subject, task, args, root) for task in pending]
            for count, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                numeric_id, record = future.result()
                records[numeric_id] = record
                status = "ok" if record["runner"]["error"] is None else "error"
                print(
                    f"{count}/{len(pending)} {record['neutral_id']} {status}",
                    flush=True,
                )
    invocation_finished = utc_now()
    _finalize_results(root, all_tasks)
    _manifest(
        root=root,
        repo_root=repo_root,
        args=args,
        invocation_started=invocation_started,
        invocation_finished=invocation_finished,
        requested=requested,
        all_tasks=all_tasks,
    )
    print(f"finalized {len(_load_completed(root))}/{len(all_tasks)} Experiment 1B records")


if __name__ == "__main__":
    main()
