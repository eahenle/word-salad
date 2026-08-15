#!/usr/bin/env python3
"""Run and freeze every subject in one authorized density stage."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path

from generate import ROOT
from runtime import EFFORT, IMAGE, MODEL, atomic_bytes, atomic_json, run_subject
from validate import validate


def paths(stage: Path, trial_id: str):
    return {"attempt": stage / "attempts" / f"{trial_id}.json", "completed": stage / "completed" / f"{trial_id}.json",
            "trace": stage / "traces" / f"{trial_id}.jsonl", "stderr": stage / "stderr" / f"{trial_id}.txt"}


def run_one(stage, row, args, freeze):
    trial_id = row["trial_id"]; artifact = paths(stage, trial_id)
    if artifact["completed"].exists(): return json.loads(artifact["completed"].read_text())
    if artifact["attempt"].exists(): raise RuntimeError(f"orphaned attempt: {trial_id}")
    prompt = stage / "prompts" / f"{trial_id}.txt"; prompt_hash = hashlib.sha256(prompt.read_bytes()).hexdigest()
    if prompt_hash != freeze["prompt_hashes"][trial_id]: raise RuntimeError(f"prompt mismatch: {trial_id}")
    atomic_json(artifact["attempt"], {"trial_id": trial_id, "prompt_sha256": prompt_hash,
                "model": MODEL, "reasoning": EFFORT, "image": IMAGE})
    run = run_subject(prompt=prompt.read_text(), auth=args.auth, timeout=args.timeout,
                      docker=args.docker, name_prefix=f"word-salad-density-{trial_id}")
    atomic_bytes(artifact["trace"], run["raw_stdout"]); atomic_bytes(artifact["stderr"], run["raw_stderr"])
    parsed = run["parsed"]
    record = {"trial_id": trial_id, "density_id": row["density_id"], "topic": row["topic"],
        "condition": row["condition"], "hidden_identity": row["hidden_identity"],
        "expected_answer": row["expected_answer"], "model": MODEL, "reasoning": EFFORT,
        "image": IMAGE, "prompt_sha256": prompt_hash, "prompt_words": len(prompt.read_text().split()),
        "response": parsed["response"] or "", "trace_file": f"development/{row['density_id']}/traces/{trial_id}.jsonl",
        "stderr_file": f"development/{row['density_id']}/stderr/{trial_id}.txt",
        "runner": {"started_at": run["started_at"], "finished_at": run["finished_at"],
            "elapsed_seconds": run["elapsed_seconds"], "thread_id": parsed["thread_id"],
            "aggregate_usage": parsed["usage"], "exit_status": run["exit_status"],
            "timed_out": run["timed_out"], "error": run["error"],
            "trace_sha256": hashlib.sha256(run["raw_stdout"]).hexdigest(),
            "stderr_sha256": hashlib.sha256(run["raw_stderr"]).hexdigest(),
            "item_type_counts": parsed["item_type_counts"]}}
    atomic_json(artifact["completed"], record); return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("density", choices=("d125", "d250"))
    parser.add_argument("--auth", type=Path, required=True); parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=600); parser.add_argument("--docker", default="docker")
    args = parser.parse_args(); validate(args.density); stage = ROOT / "development" / args.density
    freeze = json.loads((stage / "results/stage-freeze.json").read_text())
    isolation = json.loads((ROOT / "results/isolation-validation.json").read_text())
    if not isolation["passed"] or isolation["image"] != IMAGE: raise RuntimeError("isolation validation required")
    manifest = json.loads((stage / "manifest.json").read_text())
    pending = [row for row in manifest if not paths(stage, row["trial_id"])["completed"].exists()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_one, stage, row, args, freeze): row["trial_id"] for row in pending}
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            row = future.result(); print(f"{number}/{len(pending)} {row['trial_id']} {'ok' if row['runner']['error'] is None else row['runner']['error']['type']}", flush=True)
    records = [json.loads(paths(stage, row["trial_id"])["completed"].read_text()) for row in manifest]
    if len(records) != 9: raise RuntimeError("incomplete stage")
    atomic_bytes(stage / "results/trials-unscored.jsonl", "".join(json.dumps(row, ensure_ascii=False)+"\n" for row in records).encode())
    atomic_json(stage / "results/execution-freeze.json", {"density_id": args.density, "scheduled": 9,
        "completed": 9, "responses_not_inspected_before_freeze": True,
        "trace_hashes": {row["trial_id"]: row["runner"]["trace_sha256"] for row in records},
        "runner_errors": sum(row["runner"]["error"] is not None for row in records),
        "timeouts": sum(row["runner"]["timed_out"] for row in records), "direct_api_used": False})
    print(f"froze all nine {args.density} responses")


if __name__ == "__main__": main()

