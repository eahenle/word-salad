#!/usr/bin/env python3
"""Run Experiment 3 subjects in fresh pinned Docker containers."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
from collections import Counter
from pathlib import Path

from generate import Task, build_tasks
from runtime import EFFORTS, IMAGE, MODELS, atomic_bytes, atomic_json, cell_slug, run_subject
from validate import validate


def paths(root: Path, slug: str, trial_id: str) -> dict[str, Path]:
    return {
        "attempt": root / "attempts" / slug / f"{trial_id}.json",
        "completed": root / "completed" / slug / f"{trial_id}.json",
        "trace": root / "traces" / slug / f"{trial_id}.jsonl",
        "stderr": root / "stderr" / slug / f"{trial_id}.txt",
    }


def run_one(task: Task, args: argparse.Namespace, root: Path, slug: str) -> dict:
    artifact = paths(root, slug, task.neutral_id)
    if artifact["completed"].exists():
        return json.loads(artifact["completed"].read_text())
    if artifact["attempt"].exists():
        raise RuntimeError(f"{slug}/{task.neutral_id} has an active/orphaned attempt")
    artifact["attempt"].parent.mkdir(parents=True, exist_ok=True)
    atomic_json(artifact["attempt"], {
        "neutral_id": task.neutral_id,
        "model": args.model,
        "reasoning": args.reasoning,
        "carrier": task.carrier,
        "condition": task.condition,
        "payload_identity": task.payload_identity,
        "seed": task.seed,
        "prompt_sha256": task.metadata["prompt_sha256"],
        "container_image": args.image,
    })
    run = run_subject(
        prompt=task.prompt, auth=args.auth, model=args.model, effort=args.reasoning,
        timeout=args.timeout, docker=args.docker, image=args.image,
        name_prefix=f"word-salad-q3-{task.neutral_id}",
    )
    atomic_bytes(artifact["trace"], run["raw_stdout"])
    atomic_bytes(artifact["stderr"], run["raw_stderr"])
    parsed = run["parsed"]
    record = {
        "trial_id": task.neutral_id,
        "neutral_id": task.neutral_id,
        "carrier": task.carrier,
        "condition": task.condition,
        "payload_identity": task.payload_identity,
        "answer_identity": task.answer_identity,
        "lanes": 2,
        "seed": task.seed,
        "signal_phase": task.metadata["signal_phase"],
        "model": args.model,
        "reasoning": args.reasoning,
        "prompt_words": task.metadata["prompt_words"],
        "prompt_sha256": task.metadata["prompt_sha256"],
        "prompt_file": f"prompts/{task.carrier}/{task.neutral_id}.txt",
        "trace_file": f"traces/{slug}/{task.neutral_id}.jsonl",
        "stderr_file": f"stderr/{slug}/{task.neutral_id}.txt",
        "execution_origin": "fresh_experiment_3_docker_subject",
        "response": parsed["response"] or "",
        "runner": {
            "method": "codex_exec_ephemeral_container_full_trace",
            "container_image": args.image,
            "started_at": run["started_at"],
            "finished_at": run["finished_at"],
            "thread_id": parsed["thread_id"],
            "aggregate_usage": parsed["usage"],
            "elapsed_seconds": run["elapsed_seconds"],
            "exit_status": run["exit_status"],
            "timed_out": run["timed_out"],
            "error": run["error"],
            "trace_bytes": len(run["raw_stdout"]),
            "trace_sha256": __import__("hashlib").sha256(run["raw_stdout"]).hexdigest(),
            "stderr_bytes": len(run["raw_stderr"]),
            "stderr_sha256": __import__("hashlib").sha256(run["raw_stderr"]).hexdigest(),
            "event_count": parsed["event_count"],
            "event_type_counts": parsed["event_type_counts"],
            "item_type_counts": parsed["item_type_counts"],
            "non_json_line_count": parsed["non_json_line_count"],
            "error_messages": parsed["error_messages"],
        },
    }
    atomic_json(artifact["completed"], record)
    return record


def select(tasks: list[Task], args: argparse.Namespace) -> list[Task]:
    selected = list(tasks)
    if args.carriers:
        selected = [task for task in selected if task.carrier in args.carriers]
    if args.payload_identities:
        selected = [
            task for task in selected
            if (task.payload_identity or "none") in args.payload_identities
        ]
    if args.seeds:
        selected = [task for task in selected if task.seed in args.seeds]
    if args.trial_ids:
        wanted = set(args.trial_ids)
        available = {task.neutral_id for task in tasks}
        if wanted - available:
            raise ValueError(f"unknown trial IDs: {sorted(wanted - available)}")
        selected = [task for task in selected if task.neutral_id in wanted]
        if len(selected) != len(wanted):
            raise ValueError("trial IDs conflict with other selectors")
    return selected


def finalize(root: Path, slug: str, args: argparse.Namespace) -> None:
    completed = [
        json.loads(path.read_text())
        for path in sorted((root / "completed" / slug).glob("q*.json"))
    ]
    result_dir = root / "results" / "cells" / slug
    result_dir.mkdir(parents=True, exist_ok=True)
    atomic_bytes(
        result_dir / "trials-unscored.jsonl",
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in completed).encode(),
    )
    atomic_json(result_dir / "manifest.json", {
        "model": args.model,
        "reasoning": args.reasoning,
        "container_image": args.image,
        "completed_trials": len(completed),
        "completed_by_carrier": dict(sorted(Counter(record["carrier"] for record in completed).items())),
        "runner_errors": dict(sorted(Counter(
            (record["runner"].get("error") or {}).get("type", "none") for record in completed
        ).items())),
        "worker_count": args.workers,
        "timeout_seconds": args.timeout,
        "full_stdout_jsonl_preserved": True,
        "fresh_container_per_trial": True,
        "host_paths_mounted": False,
        "direct_api_used": False,
    })


def main() -> None:
    root_default = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root_default)
    parser.add_argument("--auth", type=Path, required=True)
    parser.add_argument("--isolation-validation", type=Path)
    parser.add_argument("--image", default=IMAGE)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--reasoning", choices=EFFORTS, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--carriers", nargs="+", choices=("fixed", "jitter", "all-shuffled"))
    parser.add_argument("--payload-identities", nargs="+", choices=("A", "B", "none"))
    parser.add_argument("--seeds", nargs="+", type=int, choices=range(1, 21))
    parser.add_argument("--trial-ids", nargs="+")
    parser.add_argument("--finalize-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    isolation_path = args.isolation_validation or root / "results" / "isolation-validation.json"
    isolation = json.loads(isolation_path.read_text())
    if not isolation.get("passed") or isolation.get("image") != args.image:
        raise RuntimeError("passed, image-matched isolation validation required")
    capability = json.loads((root / "results" / "capability-probe.json").read_text())
    cell = next((
        record for record in capability["cells"]
        if record["model"] == args.model and record["reasoning"] == args.reasoning
    ), None)
    if cell is None or cell["status"] != "supported":
        raise RuntimeError("exact model/reasoning cell is not recorded as supported")
    validate(root)
    tasks = build_tasks(root)
    slug = cell_slug(args.model, args.reasoning)
    if args.finalize_only:
        finalize(root, slug, args)
        return
    requested = select(tasks, args)
    pending = []
    for task in requested:
        artifact = paths(root, slug, task.neutral_id)
        if artifact["completed"].exists():
            continue
        if artifact["attempt"].exists():
            raise RuntimeError(f"{slug}/{task.neutral_id} has an orphaned attempt; no implicit retry")
        pending.append(task)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_one, task, args, root, slug): task for task in pending}
        for count, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            task = futures[future]
            record = future.result()
            error = record["runner"].get("error") or {}
            status = "ok" if not error else error["type"]
            print(f"{count}/{len(pending)} {task.neutral_id} {status}", flush=True)
            if error.get("type") in {"usage_cap", "temporary_capacity"}:
                for queued in futures:
                    queued.cancel()
                raise RuntimeError(f"{status} detected; queue halted")
    finalize(root, slug, args)
    print(f"finalized {len(list((root / 'completed' / slug).glob('q*.json')))} records for {slug}")


if __name__ == "__main__":
    main()
