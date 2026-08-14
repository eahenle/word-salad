#!/usr/bin/env python3
"""Run and freeze the nine preregistered Experiment 4C.1 subjects."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path

from runtime import EFFORT, IMAGE, MODEL, ROOT, atomic_bytes, atomic_json, run_subject
from validate import validate


def paths(trial_id: str) -> dict[str, Path]:
    base = ROOT / "development"
    return {"attempt": base / "attempts" / f"{trial_id}.json",
            "completed": base / "completed" / f"{trial_id}.json",
            "trace": base / "traces" / f"{trial_id}.jsonl",
            "stderr": base / "stderr" / f"{trial_id}.txt"}


def run_one(row: dict, args, freeze: dict) -> dict:
    trial_id = row["trial_id"]; artifact = paths(trial_id)
    if artifact["completed"].exists():
        return json.loads(artifact["completed"].read_text())
    if artifact["attempt"].exists():
        raise RuntimeError(f"orphaned attempt requires audit: {trial_id}")
    prompt_path = ROOT / "development/prompts" / f"{trial_id}.txt"
    prompt_hash = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    if prompt_hash != freeze["prompt_hashes"][trial_id]:
        raise RuntimeError(f"frozen prompt mismatch: {trial_id}")
    atomic_json(artifact["attempt"], {"trial_id": trial_id, "model": MODEL,
                "reasoning": EFFORT, "image": IMAGE, "prompt_sha256": prompt_hash})
    run = run_subject(prompt=prompt_path.read_text(), auth=args.auth, timeout=args.timeout,
                      docker=args.docker, name_prefix=f"word-salad-q4c1-{trial_id}")
    atomic_bytes(artifact["trace"], run["raw_stdout"]); atomic_bytes(artifact["stderr"], run["raw_stderr"])
    parsed = run["parsed"]
    record = {
        "trial_id": trial_id, "source_trial_id": row["source_trial_id"],
        "topic": row["topic"], "condition": row["condition"],
        "hidden_identity": row["hidden_identity"], "expected_answer": row["expected_answer"],
        "model": MODEL, "reasoning": EFFORT, "image": IMAGE,
        "prompt_sha256": prompt_hash, "prompt_words": len(prompt_path.read_text().split()),
        "response": parsed["response"] or "",
        "trace_file": f"development/traces/{trial_id}.jsonl",
        "stderr_file": f"development/stderr/{trial_id}.txt",
        "runner": {"started_at": run["started_at"], "finished_at": run["finished_at"],
                   "elapsed_seconds": run["elapsed_seconds"], "thread_id": parsed["thread_id"],
                   "aggregate_usage": parsed["usage"], "exit_status": run["exit_status"],
                   "timed_out": run["timed_out"], "error": run["error"],
                   "trace_sha256": hashlib.sha256(run["raw_stdout"]).hexdigest(),
                   "stderr_sha256": hashlib.sha256(run["raw_stderr"]).hexdigest(),
                   "trace_bytes": len(run["raw_stdout"]),
                   "event_type_counts": parsed["event_type_counts"],
                   "item_type_counts": parsed["item_type_counts"],
                   "observable_non_message_items": parsed["observable_non_message_items"]},
    }
    atomic_json(artifact["completed"], record); return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth", required=True, type=Path); parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=600); parser.add_argument("--docker", default="docker")
    args = parser.parse_args(); validate()
    freeze = json.loads((ROOT / "results/experiment-freeze.json").read_text())
    isolation = json.loads((ROOT / "results/isolation-validation.json").read_text())
    if not isolation.get("passed") or isolation.get("image") != IMAGE:
        raise RuntimeError("exact-image isolation validation required")
    manifest = json.loads((ROOT / "development/manifest.json").read_text())
    pending = [row for row in manifest if not paths(row["trial_id"])["completed"].exists()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_one, row, args, freeze): row["trial_id"] for row in pending}
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            trial_id = futures[future]; record = future.result(); error = record["runner"]["error"]
            print(f"{number}/{len(pending)} {trial_id} {'ok' if error is None else error['type']}", flush=True)
    records = [json.loads(paths(row["trial_id"])["completed"].read_text()) for row in manifest]
    if len(records) != 9:
        raise RuntimeError(f"cannot freeze incomplete cohort: {len(records)}/9")
    result_dir = ROOT / "development/results"
    atomic_bytes(result_dir / "trials-unscored.jsonl", "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in records).encode())
    atomic_json(result_dir / "execution-freeze.json", {
        "scheduled": 9, "completed": 9, "responses_not_inspected_before_freeze": True,
        "trace_hashes": {row["trial_id"]: row["runner"]["trace_sha256"] for row in records},
        "runner_errors": sum(row["runner"]["error"] is not None for row in records),
        "timeouts": sum(row["runner"]["timed_out"] for row in records),
        "direct_api_used": False,
    })
    print("froze all nine 4C.1 responses; scoring may now begin")


if __name__ == "__main__":
    main()
