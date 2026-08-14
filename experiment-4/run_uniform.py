#!/usr/bin/env python3
"""Run Experiment 4A in fresh pinned Docker containers."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from collections import Counter
from pathlib import Path

from generate_uniform import Task, build_tasks
from runtime import CELLS, IMAGE, atomic_bytes, atomic_json, cell_slug, run_subject
from validate_uniform import validate


def paths(root: Path, slug: str, trial_id: str) -> dict[str, Path]:
    base = root / "uniform"
    return {name: base / directory / slug / f"{trial_id}.{extension}" for name, directory, extension in (
        ("attempt", "attempts", "json"), ("completed", "completed", "json"),
        ("trace", "traces", "jsonl"), ("stderr", "stderr", "txt"),
    )}


def run_one(task: Task, args: argparse.Namespace, root: Path, slug: str) -> dict:
    artifact = paths(root, slug, task.neutral_id)
    if artifact["completed"].exists():
        return json.loads(artifact["completed"].read_text())
    if artifact["attempt"].exists():
        raise RuntimeError(f"{slug}/{task.neutral_id} has an orphaned attempt")
    atomic_json(artifact["attempt"], {"neutral_id": task.neutral_id, "model": args.model,
                "reasoning": args.reasoning, "condition": task.condition,
                "payload_identity": task.payload_identity, "seed": task.seed,
                "prompt_sha256": task.metadata["prompt_sha256"], "container_image": args.image})
    run = run_subject(prompt=task.prompt, auth=args.auth, model=args.model, effort=args.reasoning,
                      timeout=args.timeout, docker=args.docker, image=args.image,
                      name_prefix=f"word-salad-q4-{task.neutral_id}")
    atomic_bytes(artifact["trace"], run["raw_stdout"])
    atomic_bytes(artifact["stderr"], run["raw_stderr"])
    parsed = run["parsed"]
    record = {"trial_id": task.neutral_id, "neutral_id": task.neutral_id,
              "carrier": "uniform", "condition": task.condition,
              "payload_identity": task.payload_identity, "answer_identity": task.answer_identity,
              "lanes": 2, "seed": task.seed, "model": args.model, "reasoning": args.reasoning,
              "prompt_words": task.metadata["prompt_words"], "prompt_sha256": task.metadata["prompt_sha256"],
              "prompt_file": f"uniform/prompts/{task.neutral_id}.txt",
              "metadata_file": f"uniform/metadata/{task.neutral_id}.json",
              "trace_file": f"uniform/traces/{slug}/{task.neutral_id}.jsonl",
              "stderr_file": f"uniform/stderr/{slug}/{task.neutral_id}.txt",
              "execution_origin": "fresh_experiment_4a_docker_subject",
              "response": parsed["response"] or "",
              "runner": {"method": "codex_exec_ephemeral_container_full_trace", "container_image": args.image,
                         "started_at": run["started_at"], "finished_at": run["finished_at"],
                         "thread_id": parsed["thread_id"], "aggregate_usage": parsed["usage"],
                         "elapsed_seconds": run["elapsed_seconds"], "exit_status": run["exit_status"],
                         "timed_out": run["timed_out"], "error": run["error"],
                         "trace_bytes": len(run["raw_stdout"]),
                         "trace_sha256": hashlib.sha256(run["raw_stdout"]).hexdigest(),
                         "stderr_bytes": len(run["raw_stderr"]),
                         "stderr_sha256": hashlib.sha256(run["raw_stderr"]).hexdigest(),
                         "event_count": parsed["event_count"], "event_type_counts": parsed["event_type_counts"],
                         "item_type_counts": parsed["item_type_counts"],
                         "non_json_line_count": parsed["non_json_line_count"],
                         "error_messages": parsed["error_messages"]}}
    atomic_json(artifact["completed"], record)
    return record


def finalize(root: Path, slug: str, args: argparse.Namespace) -> None:
    completed = [json.loads(path.read_text()) for path in sorted((root / "uniform/completed" / slug).glob("q*.json"))]
    result_dir = root / "uniform/results/cells" / slug
    atomic_bytes(result_dir / "trials-unscored.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in completed).encode())
    atomic_json(result_dir / "manifest.json", {"model": args.model, "reasoning": args.reasoning,
                "container_image": args.image, "completed_trials": len(completed),
                "completed_by_condition": dict(sorted(Counter(r["condition"] for r in completed).items())),
                "runner_errors": dict(sorted(Counter((r["runner"].get("error") or {}).get("type", "none") for r in completed).items())),
                "worker_count": args.workers, "timeout_seconds": args.timeout,
                "full_stdout_jsonl_preserved": True, "fresh_container_per_trial": True,
                "host_paths_mounted": False, "direct_api_used": False})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--auth", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning", required=True)
    parser.add_argument("--image", default=IMAGE)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--seeds", nargs="+", type=int)
    parser.add_argument("--condition", choices=("signal", "all_shuffled"))
    parser.add_argument("--finalize-only", action="store_true")
    args = parser.parse_args()
    if (args.model, args.reasoning) not in CELLS:
        raise RuntimeError("exact preregistered model/reasoning cell required")
    root = args.root.resolve()
    isolation = json.loads((root / "uniform/results/isolation-validation.json").read_text())
    if not isolation.get("passed") or isolation.get("image") != args.image:
        raise RuntimeError("passed image-matched isolation validation required")
    capability = json.loads((root / "uniform/results/capability-probe.json").read_text())
    cell = next((c for c in capability["cells"] if (c["model"], c["reasoning"]) == (args.model, args.reasoning)), None)
    if cell is None or cell["status"] != "supported":
        raise RuntimeError("exact cell is not supported")
    validate(root)
    tasks = build_tasks(root)
    slug = cell_slug(args.model, args.reasoning)
    if args.finalize_only:
        finalize(root, slug, args)
        return
    if args.seeds:
        tasks = [task for task in tasks if task.seed in args.seeds]
    if args.condition:
        tasks = [task for task in tasks if task.condition == args.condition]
    pending = []
    for task in tasks:
        artifact = paths(root, slug, task.neutral_id)
        if artifact["completed"].exists():
            continue
        if artifact["attempt"].exists():
            raise RuntimeError(f"{slug}/{task.neutral_id} has an orphaned attempt; no implicit retry")
        pending.append(task)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_one, task, args, root, slug): task for task in pending}
        for count, future in enumerate(concurrent.futures.as_completed(futures), 1):
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
    print(f"finalized {len(list((root / 'uniform/completed' / slug).glob('q*.json')))} records for {slug}")


if __name__ == "__main__":
    main()
