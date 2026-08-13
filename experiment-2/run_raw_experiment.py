#!/usr/bin/env python3
"""Run the frozen Experiment 2 slate as independent tool-less API requests."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import ssl
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from generate import Task, build_tasks
from run_raw_model import load_project_api_key
from validate import validate


MODEL = "gpt-5.6-sol"
REASONING = "xhigh"
HALTING_ERROR_CODES = {
    "credit_balance_exhausted",
    "insufficient_quota",
    "rate_limit_exceeded",
}


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


def request_body(task: Task) -> bytes:
    return json.dumps(
        {
            "model": MODEL,
            "input": task.prompt,
            "reasoning": {"effort": REASONING},
            "tools": [],
            "store": False,
        },
        ensure_ascii=False,
    ).encode()


def response_summary(raw: bytes) -> dict:
    response = json.loads(raw)
    output = response.get("output") or []
    return {
        "response_id": response.get("id"),
        "object": response.get("object"),
        "status": response.get("status"),
        "model": response.get("model"),
        "error": response.get("error"),
        "incomplete_details": response.get("incomplete_details"),
        "reasoning": response.get("reasoning"),
        "store": response.get("store"),
        "tools_count": len(response.get("tools") or []),
        "output_types": [item.get("type") for item in output if isinstance(item, dict)],
        "created_at": response.get("created_at"),
        "completed_at": response.get("completed_at"),
        "usage": response.get("usage"),
    }


def validate_response(raw: bytes) -> dict:
    summary = response_summary(raw)
    if summary["object"] != "response":
        raise ValueError("API body is not a Responses response object")
    if summary["model"] != MODEL:
        raise ValueError(f"model mismatch: {summary['model']!r}")
    if summary["tools_count"] != 0:
        raise ValueError("tool-less response unexpectedly advertises tools")
    reasoning = summary.get("reasoning") or {}
    if reasoning.get("effort") != REASONING:
        raise ValueError(f"reasoning mismatch: {reasoning!r}")
    return summary


def selected_tasks(tasks: list[Task], trial_ids: list[str] | None) -> list[Task]:
    if not trial_ids:
        return tasks
    wanted = set(trial_ids)
    available = {task.neutral_id for task in tasks}
    if wanted - available:
        raise ValueError(f"unknown IDs: {sorted(wanted - available)}")
    return [task for task in tasks if task.neutral_id in wanted]


def failure_number(root: Path, neutral_id: str) -> int:
    parent = root / "raw-model" / "infrastructure-failures" / neutral_id
    existing = [
        int(path.name.split("-", 1)[1])
        for path in parent.glob("attempt-*")
        if path.name.split("-", 1)[1].isdigit()
    ]
    return max(existing, default=0) + 1


def adopt_existing(task: Task, root: Path) -> dict | None:
    response_path = root / "raw-model" / "responses" / f"{task.neutral_id}.json"
    outcome_path = root / "raw-model" / "outcomes" / f"{task.neutral_id}.json"
    attempt_path = root / "raw-model" / "attempts" / f"{task.neutral_id}.json"
    if not response_path.exists():
        return None
    raw = response_path.read_bytes()
    summary = validate_response(raw)
    if summary["error"] is not None:
        raise RuntimeError(f"{task.neutral_id} active response contains an API error")
    body = request_body(task)
    outcome = {
        "neutral_id": task.neutral_id,
        "method": "responses_api_single_request_no_tools",
        "model": MODEL,
        "reasoning_effort": REASONING,
        "tools": [],
        "store": False,
        "prompt_sha256": task.metadata["prompt_sha256"],
        "request_sha256": sha256_bytes(body),
        "response_file": str(response_path.relative_to(root)),
        "response_sha256": sha256_bytes(raw),
        "response_bytes": len(raw),
        "http_status": 200,
        "elapsed_seconds": None,
        "adopted_existing_response": True,
        "summary": summary,
    }
    if outcome_path.exists():
        existing = json.loads(outcome_path.read_text())
        if existing["response_sha256"] != outcome["response_sha256"]:
            raise RuntimeError(f"{task.neutral_id} stored outcome hash mismatch")
        return existing
    atomic_json(attempt_path, {
        "neutral_id": task.neutral_id,
        "request_sha256": sha256_bytes(body),
        "prompt_sha256": task.metadata["prompt_sha256"],
        "configuration": {
            "model": MODEL, "reasoning": {"effort": REASONING},
            "tools": [], "store": False,
        },
        "adopted_existing_response": True,
    })
    atomic_json(outcome_path, outcome)
    return outcome


def accepted_timeout(task: Task, root: Path) -> dict | None:
    path = root / "raw-model" / "timeouts" / f"{task.neutral_id}.json"
    if not path.exists():
        return None
    record = json.loads(path.read_text())
    if record["prompt_sha256"] != task.metadata["prompt_sha256"]:
        raise RuntimeError(f"{task.neutral_id} timeout prompt hash mismatch")
    return record


def is_accepted_disconnect_timeout(
    exception: str | None,
    elapsed: float,
    http_status: int | None,
    raw: bytes,
) -> bool:
    return bool(
        exception
        and "RemoteDisconnected" in exception
        and 590 <= elapsed <= 660
        and http_status is None
        and not raw
    )


def run_one(
    task: Task,
    root: Path,
    key: str,
    context: ssl.SSLContext,
    timeout: float,
    retry_ids: set[str],
    stop: threading.Event,
) -> dict:
    existing = adopt_existing(task, root)
    if existing is not None:
        return existing
    timeout_outcome = accepted_timeout(task, root)
    if timeout_outcome is not None:
        return {"neutral_id": task.neutral_id, "accepted_timeout": timeout_outcome}
    if stop.is_set():
        return {"neutral_id": task.neutral_id, "skipped_after_halt": True}
    prior_failures = list(
        (root / "raw-model" / "infrastructure-failures" / task.neutral_id).glob("attempt-*")
    )
    if prior_failures and task.neutral_id not in retry_ids:
        raise RuntimeError(
            f"{task.neutral_id} has an archived infrastructure failure; explicit retry required"
        )
    pending_path = root / "raw-model" / "pending" / f"{task.neutral_id}.json"
    if pending_path.exists():
        raise RuntimeError(f"{task.neutral_id} has an orphaned pending request")
    body = request_body(task)
    started_at = utc_now()
    began = time.monotonic()
    pending = {
        "neutral_id": task.neutral_id,
        "started_at": started_at,
        "request_sha256": sha256_bytes(body),
        "prompt_sha256": task.metadata["prompt_sha256"],
        "configuration": {
            "model": MODEL, "reasoning": {"effort": REASONING},
            "tools": [], "store": False,
        },
    }
    atomic_json(pending_path, pending)
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    raw = b""
    headers: dict[str, str] = {}
    http_status: int | None = None
    exception: str | None = None
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            http_status = response.status
            raw = response.read()
            for name in (
                "x-request-id", "openai-processing-ms", "x-ratelimit-limit-requests",
                "x-ratelimit-limit-tokens", "x-ratelimit-remaining-requests",
                "x-ratelimit-remaining-tokens", "x-ratelimit-reset-requests",
                "x-ratelimit-reset-tokens",
            ):
                if response.headers.get(name) is not None:
                    headers[name] = response.headers[name]
    except urllib.error.HTTPError as exc:
        http_status = exc.code
        raw = exc.read()
        exception = f"HTTPError({exc.code})"
    except Exception as exc:  # transport/TLS/timeouts are infrastructure events
        exception = repr(exc)
    elapsed = round(time.monotonic() - began, 3)
    finished_at = utc_now()
    if exception is not None:
        number = failure_number(root, task.neutral_id)
        archive = (
            root / "raw-model" / "infrastructure-failures" /
            task.neutral_id / f"attempt-{number}"
        )
        error_body = None
        if raw:
            try:
                error_body = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                error_body = None
            atomic_bytes(archive / "response.json", raw)
        error = (error_body or {}).get("error") or {}
        record = {
            **pending,
            "finished_at": finished_at,
            "elapsed_seconds": elapsed,
            "http_status": http_status,
            "exception": exception,
            "error_type": error.get("type"),
            "error_code": error.get("code"),
            "response_sha256": sha256_bytes(raw) if raw else None,
            "response_bytes": len(raw),
            "eligible_for_exact_retry": True,
            "inference_started": False,
        }
        atomic_json(archive / "attempt.json", record)
        pending_path.unlink()
        if is_accepted_disconnect_timeout(exception, elapsed, http_status, raw):
            timeout_record = {
                "neutral_id": task.neutral_id,
                "outcome": "timeout_nonresponse",
                "protocol_seconds": 600,
                "observed_elapsed_seconds": elapsed,
                "prompt_sha256": task.metadata["prompt_sha256"],
                "source_attempt": str((archive / "attempt.json").relative_to(root)),
                "source_attempt_sha256": sha256_bytes((archive / "attempt.json").read_bytes()),
                "response_bytes": 0,
                "retry": False,
                "decision": "accepted as a scheduled data point by coordinator instruction",
            }
            atomic_json(
                root / "raw-model" / "timeouts" / f"{task.neutral_id}.json",
                timeout_record,
            )
            return {"neutral_id": task.neutral_id, "accepted_timeout": timeout_record}
        if error.get("code") in HALTING_ERROR_CODES or error.get("type") in HALTING_ERROR_CODES:
            stop.set()
        return {"neutral_id": task.neutral_id, "infrastructure_failure": record}
    summary = validate_response(raw)
    response_path = root / "raw-model" / "responses" / f"{task.neutral_id}.json"
    outcome_path = root / "raw-model" / "outcomes" / f"{task.neutral_id}.json"
    attempt_path = root / "raw-model" / "attempts" / f"{task.neutral_id}.json"
    atomic_bytes(response_path, raw)
    outcome = {
        "neutral_id": task.neutral_id,
        "method": "responses_api_single_request_no_tools",
        "model": MODEL,
        "reasoning_effort": REASONING,
        "tools": [],
        "store": False,
        "prompt_sha256": task.metadata["prompt_sha256"],
        "request_sha256": sha256_bytes(body),
        "response_file": str(response_path.relative_to(root)),
        "response_sha256": sha256_bytes(raw),
        "response_bytes": len(raw),
        "http_status": http_status,
        "response_headers": headers,
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_seconds": elapsed,
        "adopted_existing_response": False,
        "summary": summary,
    }
    atomic_json(attempt_path, {**pending, "finished_at": finished_at})
    atomic_json(outcome_path, outcome)
    pending_path.unlink()
    return outcome


def finalize(root: Path, total: int, workers: int, timeout: float) -> dict:
    outcomes = [
        json.loads(path.read_text())
        for path in sorted((root / "raw-model" / "outcomes").glob("r*.json"))
    ]
    timeouts = [
        json.loads(path.read_text())
        for path in sorted((root / "raw-model" / "timeouts").glob("r*.json"))
    ]
    terminal_ids = {record["neutral_id"] for record in outcomes + timeouts}
    unresolved_failures = [
        json.loads(path.read_text())
        for path in sorted(
            (root / "raw-model" / "infrastructure-failures").glob("r*/attempt-*/attempt.json")
        )
        if json.loads(path.read_text())["neutral_id"] not in terminal_ids
    ]
    statuses = Counter(record["summary"].get("status") for record in outcomes)
    report = {
        "experiment": "Experiment 2 exact tool-less comparison",
        "model": MODEL,
        "reasoning_effort": REASONING,
        "tools": [],
        "store": False,
        "scheduled_trials": total,
        "scheduled_outcomes": len(outcomes) + len(timeouts),
        "completed_responses": len(outcomes),
        "timeout_nonresponses": len(timeouts),
        "unresolved_infrastructure_failures": len(unresolved_failures),
        "response_statuses": dict(sorted(statuses.items())),
        "workers": workers,
        "timeout_seconds": timeout,
        "raw_api_responses_preserved": True,
        "fresh_independent_request_per_trial": True,
        "prior_response_context_used": False,
        "finalized_at": utc_now(),
    }
    atomic_json(root / "results" / "raw-model-manifest.json", report)
    return report


def main() -> None:
    root_default = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root_default)
    parser.add_argument("--env-file", type=Path, default=root_default.parent / ".env")
    parser.add_argument("--ca-file", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--trial-ids", nargs="+")
    parser.add_argument("--retry-trial-ids", nargs="+", default=[])
    args = parser.parse_args()
    root = args.root.resolve()
    validate(root)
    tasks = build_tasks(root)
    requested = selected_tasks(tasks, args.trial_ids)
    key = load_project_api_key(args.env_file)
    if not key:
        raise SystemExit("OPENAI_API_KEY is not configured")
    context = ssl.create_default_context()
    if args.ca_file:
        context.load_verify_locations(cafile=args.ca_file)
    stop = threading.Event()
    retry_ids = set(args.retry_trial_ids)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                run_one, task, root, key, context, args.timeout, retry_ids, stop
            ): task
            for task in requested
        }
        for count, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            task = futures[future]
            result = future.result()
            results.append(result)
            if result.get("infrastructure_failure"):
                status = "infrastructure-failure"
            elif result.get("accepted_timeout"):
                status = "timeout-nonresponse"
            elif result.get("skipped_after_halt"):
                status = "skipped-after-halt"
            else:
                status = result["summary"].get("status")
            print(f"{count}/{len(requested)} {task.neutral_id} {status}", flush=True)
            if stop.is_set():
                for queued in futures:
                    queued.cancel()
    report = finalize(root, len(tasks), args.workers, args.timeout)
    failures = [result for result in results if result.get("infrastructure_failure")]
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(f"{len(failures)} infrastructure failures preserved; exact retry required")


if __name__ == "__main__":
    main()
