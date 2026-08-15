#!/usr/bin/env python3
"""Run and freeze one authorized five-symbol validation cohort."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path

from generate_clean import ROOT
from runtime import EFFORT, IMAGE, MODEL, atomic_bytes, atomic_json, run_subject
from validate import EXPECTED_COUNTS, validate


def paths(cohort: str, trial_id: str) -> dict[str, Path]:
    base = ROOT / "cohorts" / cohort
    return {
        "attempt": base / "attempts" / f"{trial_id}.json",
        "completed": base / "completed" / f"{trial_id}.json",
        "trace": base / "traces" / f"{trial_id}.jsonl",
        "stderr": base / "stderr" / f"{trial_id}.txt",
    }


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def authorize(cohort: str) -> None:
    if cohort == "clean":
        return
    gate_path = ROOT / "results/clean-gate.json"
    if not gate_path.exists():
        raise RuntimeError("clean cohort has not been scored")
    if not json.loads(gate_path.read_text()).get("advance_scrambled_authorized"):
        raise RuntimeError("clean gate does not authorize scrambled controls")


def run_one(cohort: str, row: dict, args: argparse.Namespace, freeze: dict) -> dict:
    trial_id = row["trial_id"]
    artifact = paths(cohort, trial_id)
    if artifact["completed"].exists():
        return json.loads(artifact["completed"].read_text())
    if artifact["attempt"].exists():
        raise RuntimeError(f"orphaned attempt requires explicit audit: {trial_id}")
    prompt_path = ROOT / row["prompt_file"]
    prompt_bytes = prompt_path.read_bytes()
    prompt_hash = sha256(prompt_bytes)
    if freeze["prompt_hashes"].get(trial_id) != prompt_hash:
        raise RuntimeError(f"frozen prompt mismatch: {trial_id}")
    atomic_json(artifact["attempt"], {
        "trial_id": trial_id,
        "cohort": cohort,
        "prompt_sha256": prompt_hash,
        "model": MODEL,
        "reasoning": EFFORT,
        "image": IMAGE,
    })
    run = run_subject(
        prompt=prompt_bytes.decode(),
        auth=args.auth,
        timeout=args.timeout,
        docker=args.docker,
        name_prefix=f"word-salad-q6-{trial_id}",
    )
    atomic_bytes(artifact["trace"], run["raw_stdout"])
    atomic_bytes(artifact["stderr"], run["raw_stderr"])
    parsed = run["parsed"]
    record = {
        **row,
        "model": MODEL,
        "reasoning": EFFORT,
        "image": IMAGE,
        "response": parsed["response"] or "",
        "trace_file": str(artifact["trace"].relative_to(ROOT)),
        "stderr_file": str(artifact["stderr"].relative_to(ROOT)),
        "runner": {
            "started_at": run["started_at"],
            "finished_at": run["finished_at"],
            "elapsed_seconds": run["elapsed_seconds"],
            "thread_id": parsed["thread_id"],
            "aggregate_usage": parsed["usage"],
            "exit_status": run["exit_status"],
            "timed_out": run["timed_out"],
            "error": run["error"],
            "trace_sha256": sha256(run["raw_stdout"]),
            "stderr_sha256": sha256(run["raw_stderr"]),
            "trace_bytes": len(run["raw_stdout"]),
            "event_type_counts": parsed["event_type_counts"],
            "item_type_counts": parsed["item_type_counts"],
            "observable_non_message_items": parsed["observable_non_message_items"],
        },
    }
    atomic_json(artifact["completed"], record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cohort", choices=tuple(EXPECTED_COUNTS))
    parser.add_argument("--auth", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--docker", default="docker")
    args = parser.parse_args()
    if args.workers != 3 or args.timeout != 600:
        raise RuntimeError("frozen execution requires workers=3 and timeout=600")
    validate(require_freeze=True)
    authorize(args.cohort)
    isolation = json.loads((ROOT / "results/isolation-validation.json").read_text())
    if not isolation.get("passed") or isolation.get("image") != IMAGE:
        raise RuntimeError("exact-image isolation validation is required")
    cohort_root = ROOT / "cohorts" / args.cohort
    execution_path = cohort_root / "results/execution-freeze.json"
    if execution_path.exists():
        raise RuntimeError(f"cohort already frozen: {args.cohort}")
    freeze = json.loads((ROOT / "results/protocol-freeze.json").read_text())
    manifest = json.loads((cohort_root / "manifest.json").read_text())
    by_id = {row["trial_id"]: row for row in manifest["trials"]}
    ordered = [by_id[trial_id] for trial_id in manifest["query_order"]]
    pending = [row for row in ordered if not paths(args.cohort, row["trial_id"])["completed"].exists()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(run_one, args.cohort, row, args, freeze): row["trial_id"]
            for row in pending
        }
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            trial_id = futures[future]
            record = future.result()
            error = record["runner"]["error"]
            status = "ok" if error is None else error["type"]
            print(f"{number}/{len(pending)} {trial_id} {status}", flush=True)
    records = [
        json.loads(paths(args.cohort, row["trial_id"])["completed"].read_text())
        for row in ordered
    ]
    expected = EXPECTED_COUNTS[args.cohort]
    if len(records) != expected:
        raise RuntimeError(f"cannot freeze incomplete cohort: {len(records)}/{expected}")
    result_dir = cohort_root / "results"
    atomic_bytes(result_dir / "trials-unscored.jsonl", "".join(
        json.dumps(record, ensure_ascii=False) + "\n" for record in records
    ).encode())
    atomic_json(execution_path, {
        "cohort": args.cohort,
        "scheduled": expected,
        "completed": expected,
        "responses_not_inspected_before_freeze": True,
        "query_order": manifest["query_order"],
        "trace_hashes": {
            row["trial_id"]: row["runner"]["trace_sha256"] for row in records
        },
        "runner_errors": sum(row["runner"]["error"] is not None for row in records),
        "timeouts": sum(row["runner"]["timed_out"] for row in records),
        "direct_api_used": False,
    })
    print(f"froze all {expected} {args.cohort} responses; scoring may begin")


if __name__ == "__main__":
    main()
