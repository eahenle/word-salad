#!/usr/bin/env python3
"""Run and freeze the v2 clean-validation cohort."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path

from runtime import EFFORT, IMAGE, MODEL, ROOT, atomic_bytes, atomic_json, run_subject


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def paths(trial_id: str) -> dict[str, Path]:
    base = ROOT / "cohorts/clean"
    return {
        "attempt": base / "attempts" / f"{trial_id}.json",
        "completed": base / "completed" / f"{trial_id}.json",
        "trace": base / "traces" / f"{trial_id}.jsonl",
        "stderr": base / "stderr" / f"{trial_id}.txt",
    }


def verify(freeze: dict, manifest: dict) -> None:
    if len(manifest["trials"]) != 40 or len(set(manifest["query_order"])) != 40:
        raise RuntimeError("invalid frozen clean manifest")
    for row in manifest["trials"]:
        prompt = ROOT / row["prompt_file"]
        if sha256(prompt.read_bytes()) != freeze["prompt_hashes"].get(row["trial_id"]):
            raise RuntimeError(f"prompt hash mismatch: {row['trial_id']}")
    for name, expected in freeze["source_hashes"].items():
        if sha256((ROOT / name).read_bytes()) != expected:
            raise RuntimeError(f"frozen source changed: {name}")


def run_one(row: dict, args: argparse.Namespace, freeze: dict) -> dict:
    trial_id = row["trial_id"]
    artifact = paths(trial_id)
    if artifact["completed"].exists():
        return json.loads(artifact["completed"].read_text())
    if artifact["attempt"].exists():
        raise RuntimeError(f"orphaned attempt requires audit: {trial_id}")
    prompt_bytes = (ROOT / row["prompt_file"]).read_bytes()
    prompt_hash = sha256(prompt_bytes)
    if prompt_hash != freeze["prompt_hashes"].get(trial_id):
        raise RuntimeError(f"frozen prompt mismatch: {trial_id}")
    atomic_json(artifact["attempt"], {
        "trial_id": trial_id,
        "prompt_sha256": prompt_hash,
        "model": MODEL,
        "reasoning": EFFORT,
        "image": IMAGE,
    })
    run = run_subject(
        prompt=prompt_bytes.decode(), auth=args.auth, timeout=args.timeout,
        docker=args.docker, name_prefix=f"word-salad-q6v2-{trial_id}",
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
    parser.add_argument("--auth", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--docker", default="docker")
    args = parser.parse_args()
    if args.workers != 3 or args.timeout != 600:
        raise RuntimeError("frozen execution requires workers=3 and timeout=600")
    result_dir = ROOT / "cohorts/clean/results"
    if (result_dir / "execution-freeze.json").exists():
        raise RuntimeError("v2 clean cohort already frozen")
    freeze = json.loads((ROOT / "results/protocol-freeze.json").read_text())
    manifest = json.loads((ROOT / "cohorts/clean/manifest.json").read_text())
    verify(freeze, manifest)
    isolation = json.loads((ROOT.parent / "five-symbol/results/isolation-validation.json").read_text())
    if not isolation.get("passed") or isolation.get("image") != IMAGE:
        raise RuntimeError("exact-image isolation validation is required")
    by_id = {row["trial_id"]: row for row in manifest["trials"]}
    ordered = [by_id[trial_id] for trial_id in manifest["query_order"]]
    pending = [row for row in ordered if not paths(row["trial_id"])["completed"].exists()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_one, row, args, freeze): row["trial_id"] for row in pending}
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            trial_id = futures[future]
            record = future.result()
            error = record["runner"]["error"]
            print(f"{number}/{len(pending)} {trial_id} {'ok' if error is None else error['type']}", flush=True)
    records = [json.loads(paths(row["trial_id"])["completed"].read_text()) for row in ordered]
    if len(records) != 40:
        raise RuntimeError("cannot freeze incomplete v2 clean cohort")
    atomic_bytes(result_dir / "trials-unscored.jsonl", "".join(
        json.dumps(record, ensure_ascii=False) + "\n" for record in records
    ).encode())
    atomic_json(result_dir / "execution-freeze.json", {
        "cohort": "clean-v2",
        "scheduled": 40,
        "completed": 40,
        "responses_not_inspected_before_freeze": True,
        "query_order": manifest["query_order"],
        "trace_hashes": {row["trial_id"]: row["runner"]["trace_sha256"] for row in records},
        "runner_errors": sum(row["runner"]["error"] is not None for row in records),
        "timeouts": sum(row["runner"]["timed_out"] for row in records),
        "direct_api_used": False,
    })
    print("froze all 40 v2 clean responses; scoring may begin")


if __name__ == "__main__":
    main()
