#!/usr/bin/env python3
"""Run and hash-freeze ten sterile C1 retrieval probes without printing responses."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path

from runtime import EFFORT, IMAGE, MODEL, atomic_bytes, atomic_json, run_subject
from validate import ROOT, load_labels, validate


def paths(trial_id: str) -> dict[str, Path]:
    private = ROOT / "private"
    return {
        "attempt": private / "attempts" / f"{trial_id}.json",
        "completed": private / "completed" / f"{trial_id}.json",
        "trace": private / "traces" / f"{trial_id}.jsonl",
        "stderr": private / "stderr" / f"{trial_id}.txt",
    }


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run_one(row: dict, args: argparse.Namespace, freeze: dict) -> dict:
    trial_id = row["trial_id"]
    artifact = paths(trial_id)
    if artifact["completed"].exists():
        return json.loads(artifact["completed"].read_text())
    if artifact["attempt"].exists():
        raise RuntimeError(f"orphaned attempt requires explicit transport audit: {trial_id}")
    prompt_path = ROOT / "prompts" / f"{trial_id}.txt"
    prompt_bytes = prompt_path.read_bytes()
    prompt_hash = sha256(prompt_bytes)
    if freeze["prompt_hashes"].get(trial_id) != prompt_hash:
        raise RuntimeError(f"frozen prompt mismatch: {trial_id}")
    atomic_json(artifact["attempt"], {
        "trial_id": trial_id,
        "label": row["label"],
        "allocation": row["allocation"],
        "prompt_sha256": prompt_hash,
        "model": MODEL,
        "reasoning": EFFORT,
        "image": IMAGE,
    })
    run = run_subject(
        prompt=prompt_bytes.decode(), auth=args.auth, timeout=args.timeout,
        docker=args.docker, name_prefix=f"word-salad-q5-cloud-{trial_id}",
    )
    atomic_bytes(artifact["trace"], run["raw_stdout"])
    atomic_bytes(artifact["stderr"], run["raw_stderr"])
    parsed = run["parsed"]
    response = parsed["response"] or ""
    record = {
        "trial_id": trial_id,
        "label": row["label"],
        "allocation": row["allocation"],
        "model": MODEL,
        "reasoning": EFFORT,
        "image": IMAGE,
        "prompt_sha256": prompt_hash,
        "response": response,
        "trace_file_private": f"private/traces/{trial_id}.jsonl",
        "stderr_file_private": f"private/stderr/{trial_id}.txt",
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
            "response_sha256": sha256(response.encode()),
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
    parser.add_argument("--auth", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--docker", default="docker")
    args = parser.parse_args()
    if args.timeout != 600:
        raise RuntimeError("the frozen timeout is exactly 600 seconds")
    if args.workers != 1:
        raise RuntimeError("the frozen C1 cohort uses one worker")
    validate()
    freeze = json.loads((ROOT / "results/freeze.json").read_text())
    isolation_path = ROOT / "results/isolation-validation.json"
    if not isolation_path.exists():
        raise RuntimeError("run validate_isolation.py before subject execution")
    isolation = json.loads(isolation_path.read_text())
    if not isolation.get("passed") or isolation.get("image") != IMAGE:
        raise RuntimeError("exact-image isolation validation is required")
    output = ROOT / "results/execution-freeze.json"
    if output.exists():
        raise RuntimeError("execution cohort is already frozen; do not rerun it")
    manifest, by_id = load_labels()
    ordered = [by_id[trial_id] for trial_id in manifest["query_order"]]
    pending = [row for row in ordered if not paths(row["trial_id"])["completed"].exists()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_one, row, args, freeze): row["trial_id"] for row in pending}
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            trial_id = futures[future]
            record = future.result()
            error = record["runner"]["error"]
            status = "ok" if error is None else error["type"]
            print(f"{number}/{len(pending)} {trial_id} {status}", flush=True)
    records = [json.loads(paths(row["trial_id"])["completed"].read_text()) for row in ordered]
    if len(records) != 10:
        raise RuntimeError(f"cannot freeze incomplete cohort: {len(records)}/10")
    public_rows = []
    for record in records:
        runner = record["runner"]
        public_rows.append({
            "trial_id": record["trial_id"],
            "label": record["label"],
            "allocation": record["allocation"],
            "prompt_sha256": record["prompt_sha256"],
            "response_sha256": runner["response_sha256"],
            "trace_sha256": runner["trace_sha256"],
            "stderr_sha256": runner["stderr_sha256"],
            "elapsed_seconds": runner["elapsed_seconds"],
            "thread_id": runner["thread_id"],
            "aggregate_usage": runner["aggregate_usage"],
            "exit_status": runner["exit_status"],
            "timed_out": runner["timed_out"],
            "error": runner["error"],
            "trace_bytes": runner["trace_bytes"],
            "event_type_counts": runner["event_type_counts"],
            "item_type_counts": runner["item_type_counts"],
            "observable_non_message_items": runner["observable_non_message_items"],
        })
    execution_freeze = {
        "schema_version": 1,
        "scheduled": 10,
        "completed": 10,
        "query_order": manifest["query_order"],
        "responses_not_printed_by_runner": True,
        "responses_not_inspected_before_freeze": True,
        "expected_values_supplied_before_freeze": False,
        "raw_artifacts_location": "Git-ignored private/ tree",
        "runner_errors": sum(row["error"] is not None for row in public_rows),
        "timeouts": sum(row["timed_out"] for row in public_rows),
        "direct_api_used": False,
        "trials": public_rows,
    }
    atomic_json(output, execution_freeze)
    print("froze ten response/trace hashes; unblinding may now begin")


if __name__ == "__main__":
    main()
