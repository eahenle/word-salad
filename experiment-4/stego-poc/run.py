#!/usr/bin/env python3
"""Run frozen Experiment 4B stimuli in fresh capability-limited containers."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from collections import Counter
from pathlib import Path

from cover_generator import DEFENSES, build
from poc_runtime import EFFORT, IMAGE, MODEL, atomic_bytes, atomic_json, run_subject
from validate import EXPECTED, validate


def artifacts(root: Path, set_name: str, trial_id: str) -> dict[str, Path]:
    base = root / set_name
    return {name: base / directory / f"{trial_id}.{suffix}" for name, directory, suffix in (
        ("attempt", "attempts", "json"), ("completed", "completed", "json"),
        ("trace", "traces", "jsonl"), ("stderr", "stderr", "txt"))}


def frozen_hashes(root: Path) -> dict[str, str]:
    freeze = json.loads((root / "results/stimulus-freeze.json").read_text())
    return freeze["prompt_hashes"]


def run_one(item, root: Path, args: argparse.Namespace, hashes: dict[str, str]) -> dict:
    paths = artifacts(root, args.set_name, item.neutral_id)
    if paths["completed"].exists(): return json.loads(paths["completed"].read_text())
    if paths["attempt"].exists(): raise RuntimeError(f"orphaned attempt: {item.neutral_id}")
    prompt_sha = hashlib.sha256(item.prompt.encode()).hexdigest()
    if hashes.get(item.neutral_id) != prompt_sha: raise RuntimeError(f"prompt freeze mismatch: {item.neutral_id}")
    atomic_json(paths["attempt"], {"neutral_id": item.neutral_id, "prompt_sha256": prompt_sha,
                "model": MODEL, "reasoning": EFFORT, "container_image": IMAGE})
    run = run_subject(prompt=item.prompt, defense=DEFENSES[item.defense], auth=args.auth,
                      timeout=args.timeout, docker=args.docker, name_prefix=f"word-salad-q4b-{item.neutral_id}")
    atomic_bytes(paths["trace"], run["raw_stdout"]); atomic_bytes(paths["stderr"], run["raw_stderr"])
    parsed = run["parsed"]
    marker_labels = [entry.get("label") for entry in run["markers"] if isinstance(entry, dict)]
    record = {"trial_id": item.neutral_id, "neutral_id": item.neutral_id,
              "set": args.set_name, "topic_id": item.topic_id, "condition": item.condition,
              "defense": item.defense, "hidden_identity": item.hidden_identity,
              "expected_marker": item.expected_marker, "model": MODEL, "reasoning": EFFORT,
              "document_word_count": item.metadata["document_word_count"],
              "prompt_sha256": prompt_sha, "document_sha256": item.metadata["document_sha256"],
              "prompt_file": f"{args.set_name}/prompts/{item.neutral_id}.txt",
              "trace_file": f"{args.set_name}/traces/{item.neutral_id}.jsonl",
              "stderr_file": f"{args.set_name}/stderr/{item.neutral_id}.txt",
              "response": parsed["response"] or "", "marker_labels": marker_labels,
              "marker_log": run["markers"], "runner": {"method": "codex_exec_ephemeral_container_full_trace",
                  "container_image": IMAGE, "started_at": run["started_at"], "finished_at": run["finished_at"],
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
    atomic_json(paths["completed"], record); return record


def finalize(root: Path, set_name: str, args: argparse.Namespace) -> None:
    directory = root / set_name / "completed"
    records = [json.loads(path.read_text()) for path in sorted(directory.glob("*.json"))]
    if len(records) != EXPECTED[set_name]:
        raise RuntimeError(f"cannot freeze {set_name}: {len(records)}/{EXPECTED[set_name]} completed")
    result = root / set_name / "results"; result.mkdir(parents=True, exist_ok=True)
    atomic_bytes(result / "trials-unscored.jsonl",
                 "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records).encode())
    freeze = {"set": set_name, "scheduled_trials": EXPECTED[set_name], "completed_trials": len(records),
              "condition_counts": dict(sorted(Counter(r["condition"] for r in records).items())),
              "defense_counts": dict(sorted(Counter(r["defense"] for r in records).items())),
              "runner_error_counts": dict(sorted(Counter((r["runner"].get("error") or {}).get("type", "none") for r in records).items())),
              "trace_hashes": {r["neutral_id"]: r["runner"]["trace_sha256"] for r in records},
              "full_trace_preserved": True, "fresh_container_per_trial": True,
              "host_paths_mounted": False, "direct_api_used": False,
              "responses_not_inspected_before_freeze": True,
              "worker_count": args.workers, "timeout_seconds": args.timeout}
    atomic_json(result / "execution-freeze.json", freeze)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", dest="set_name", required=True, choices=tuple(EXPECTED))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--auth", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--finalize-only", action="store_true")
    args = parser.parse_args(); root = args.root.resolve()
    validate(root)
    isolation = json.loads((root / "results/isolation-validation.json").read_text())
    if not isolation.get("passed") or isolation.get("image") != IMAGE:
        raise RuntimeError("passed image-matched isolation audit required")
    hashes = frozen_hashes(root); items = build(args.set_name)
    if args.finalize_only: finalize(root, args.set_name, args); return
    pending = []
    for item in items:
        paths = artifacts(root, args.set_name, item.neutral_id)
        if paths["completed"].exists(): continue
        if paths["attempt"].exists(): raise RuntimeError(f"orphaned attempt: {item.neutral_id}")
        pending.append(item)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_one, item, root, args, hashes): item for item in pending}
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            item = futures[future]; record = future.result(); error = record["runner"].get("error") or {}
            print(f"{number}/{len(pending)} {item.neutral_id} {'ok' if not error else error['type']}", flush=True)
    finalize(root, args.set_name, args)
    print(f"froze {EXPECTED[args.set_name]} {args.set_name} trials")


if __name__ == "__main__":
    main()
