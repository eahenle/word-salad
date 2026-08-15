#!/usr/bin/env python3
"""Run and freeze one authorized balanced-density stage."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path

from generate import ROOT, STAGES
from runtime import EFFORT, IMAGE, MODEL, atomic_bytes, atomic_json, run_subject
from validate import validate


ORDER = list(STAGES)


def paths(stage: str, trial_id: str) -> dict[str, Path]:
    base = ROOT / "stages" / stage
    return {
        "attempt": base / "attempts" / f"{trial_id}.json",
        "completed": base / "completed" / f"{trial_id}.json",
        "trace": base / "traces" / f"{trial_id}.jsonl",
        "stderr": base / "stderr" / f"{trial_id}.txt",
    }


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def authorization(stage: str) -> None:
    index = ORDER.index(stage)
    if index == 0:
        return
    previous = ORDER[index - 1]
    gate_path = ROOT / "stages" / previous / "results/development-gate.json"
    if not gate_path.exists():
        raise RuntimeError(f"prior stage is not scored: {previous}")
    gate = json.loads(gate_path.read_text())
    if not gate.get("advance_authorized") or gate.get("next_stage") != stage:
        raise RuntimeError(f"prior gate does not authorize {stage}")


def run_one(stage: str, row: dict, args: argparse.Namespace, freeze: dict) -> dict:
    trial_id = row["trial_id"]
    artifact = paths(stage, trial_id)
    if artifact["completed"].exists():
        return json.loads(artifact["completed"].read_text())
    if artifact["attempt"].exists():
        raise RuntimeError(f"orphaned attempt requires explicit transport audit: {trial_id}")
    prompt_path = ROOT / "stages" / stage / "prompts" / f"{trial_id}.txt"
    prompt_bytes = prompt_path.read_bytes()
    prompt_hash = sha256(prompt_bytes)
    if freeze["prompt_hashes"].get(trial_id) != prompt_hash:
        raise RuntimeError(f"frozen prompt mismatch: {trial_id}")
    atomic_json(artifact["attempt"], {
        "trial_id": trial_id, "stage": stage, "prompt_sha256": prompt_hash,
        "model": MODEL, "reasoning": EFFORT, "image": IMAGE,
    })
    run = run_subject(prompt=prompt_bytes.decode(), auth=args.auth, timeout=args.timeout,
                      docker=args.docker, name_prefix=f"word-salad-q5-{trial_id}")
    atomic_bytes(artifact["trace"], run["raw_stdout"])
    atomic_bytes(artifact["stderr"], run["raw_stderr"])
    parsed = run["parsed"]
    record = {
        "trial_id": trial_id, "stage": stage, "seed": row["seed"],
        "condition": row["condition"], "hidden_identity": row["hidden_identity"],
        "expected_answer": row["expected_answer"], "actual_density": row["actual_density"],
        "model": MODEL, "reasoning": EFFORT, "image": IMAGE,
        "prompt_sha256": prompt_hash, "prompt_words": row["prompt_words"],
        "response": parsed["response"] or "",
        "trace_file": f"stages/{stage}/traces/{trial_id}.jsonl",
        "stderr_file": f"stages/{stage}/stderr/{trial_id}.txt",
        "runner": {
            "started_at": run["started_at"], "finished_at": run["finished_at"],
            "elapsed_seconds": run["elapsed_seconds"], "thread_id": parsed["thread_id"],
            "aggregate_usage": parsed["usage"], "exit_status": run["exit_status"],
            "timed_out": run["timed_out"], "error": run["error"],
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
    parser.add_argument("stage", choices=ORDER)
    parser.add_argument("--auth", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--docker", default="docker")
    args = parser.parse_args()
    if args.workers != 3 or args.timeout != 600:
        raise RuntimeError("frozen execution requires workers=3 and timeout=600")
    validate(require_freeze=True)
    authorization(args.stage)
    isolation = json.loads((ROOT / "results/isolation-validation.json").read_text())
    if not isolation.get("passed") or isolation.get("image") != IMAGE:
        raise RuntimeError("exact-image isolation validation is required")
    stage_root = ROOT / "stages" / args.stage
    execution_path = stage_root / "results/execution-freeze.json"
    if execution_path.exists():
        raise RuntimeError(f"stage is already frozen: {args.stage}")
    freeze = json.loads((ROOT / "results/protocol-freeze.json").read_text())
    manifest = json.loads((stage_root / "manifest.json").read_text())
    by_id = {row["trial_id"]: row for row in manifest["trials"]}
    ordered = [by_id[trial_id] for trial_id in manifest["query_order"]]
    pending = [row for row in ordered if not paths(args.stage, row["trial_id"])["completed"].exists()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_one, args.stage, row, args, freeze): row["trial_id"] for row in pending}
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            trial_id = futures[future]
            record = future.result()
            error = record["runner"]["error"]
            print(f"{number}/{len(pending)} {trial_id} {'ok' if error is None else error['type']}", flush=True)
    records = [json.loads(paths(args.stage, row["trial_id"])["completed"].read_text()) for row in ordered]
    if len(records) != 9:
        raise RuntimeError(f"cannot freeze incomplete stage: {len(records)}/9")
    result_dir = stage_root / "results"
    atomic_bytes(result_dir / "trials-unscored.jsonl", "".join(
        json.dumps(record, ensure_ascii=False) + "\n" for record in records
    ).encode())
    atomic_json(execution_path, {
        "stage": args.stage, "scheduled": 9, "completed": 9,
        "responses_not_inspected_before_freeze": True,
        "query_order": manifest["query_order"],
        "trace_hashes": {row["trial_id"]: row["runner"]["trace_sha256"] for row in records},
        "runner_errors": sum(row["runner"]["error"] is not None for row in records),
        "timeouts": sum(row["runner"]["timed_out"] for row in records),
        "direct_api_used": False,
    })
    print(f"froze all nine {args.stage} responses; scoring may now begin")


if __name__ == "__main__":
    main()
