#!/usr/bin/env python3
"""Run and freeze the four Arm A raw-text development subjects."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path

from runtime import EFFORT, IMAGE, MODEL, atomic_bytes, atomic_json, run_subject
from validate import PARENT, ROOT, validate


def artifacts(trial_id: str) -> dict[str, Path]:
    base = ROOT / "development/raw"
    return {name: base / directory / f"{trial_id}.{suffix}" for name, directory, suffix in (
        ("attempt", "attempts", "json"), ("completed", "completed", "json"),
        ("trace", "traces", "jsonl"), ("stderr", "stderr", "txt"),
        ("marker", "marker-logs", "json"))}


def run_one(trial_id: str, reference: dict, args, prompt_hashes: dict) -> dict:
    paths = artifacts(trial_id)
    if paths["completed"].exists(): return json.loads(paths["completed"].read_text())
    if paths["attempt"].exists(): raise RuntimeError(f"orphaned attempt: {trial_id}")
    prompt_path = PARENT / "development/documents" / f"{trial_id}.txt"; prompt_bytes = prompt_path.read_bytes()
    prompt_hash = hashlib.sha256(prompt_bytes).hexdigest()
    if prompt_hashes.get(trial_id) != prompt_hash: raise RuntimeError(f"frozen prompt mismatch: {trial_id}")
    atomic_json(paths["attempt"], {"trial_id": trial_id, "arm": "raw", "prompt_sha256": prompt_hash,
                "model": MODEL, "reasoning": EFFORT, "image": IMAGE})
    run = run_subject(prompt=prompt_bytes.decode(), auth=args.auth, timeout=args.timeout,
                      docker=args.docker, name_prefix=f"word-salad-q4b1-{trial_id}")
    atomic_bytes(paths["trace"], run["raw_stdout"]); atomic_bytes(paths["stderr"], run["raw_stderr"])
    atomic_json(paths["marker"], run["markers"]); parsed = run["parsed"]
    record = {"trial_id": trial_id, "topic_id": reference["topic"], "arm": "raw",
              "hidden_identity": reference["identity"], "expected_marker": reference["expected_marker"],
              "model": MODEL, "reasoning": EFFORT, "prompt_sha256": prompt_hash,
              "prompt_origin": f"../development/documents/{trial_id}.txt",
              "custom_developer_instructions": None, "user_prefix": "", "user_suffix": "",
              "response": parsed["response"] or "", "marker_log": run["markers"],
              "marker_labels": [x.get("label") for x in run["markers"] if isinstance(x, dict)],
              "trace_file": f"development/raw/traces/{trial_id}.jsonl",
              "stderr_file": f"development/raw/stderr/{trial_id}.txt",
              "marker_log_file": f"development/raw/marker-logs/{trial_id}.json",
              "runner": {"image": IMAGE, "started_at": run["started_at"], "finished_at": run["finished_at"],
                  "elapsed_seconds": run["elapsed_seconds"], "thread_id": parsed["thread_id"],
                  "aggregate_usage": parsed["usage"], "exit_status": run["exit_status"],
                  "timed_out": run["timed_out"], "error": run["error"],
                  "trace_sha256": hashlib.sha256(run["raw_stdout"]).hexdigest(),
                  "stderr_sha256": hashlib.sha256(run["raw_stderr"]).hexdigest(),
                  "event_type_counts": parsed["event_type_counts"],
                  "item_type_counts": parsed["item_type_counts"]}}
    atomic_json(paths["completed"], record); return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--auth", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4); parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--docker", default="docker"); args = parser.parse_args()
    validate(); protocol = json.loads((ROOT / "results/protocol-freeze.json").read_text())
    isolation = json.loads((ROOT / "results/isolation-validation.json").read_text())
    if not isolation.get("passed") or isolation.get("image") != IMAGE: raise RuntimeError("image-matched isolation validation required")
    references = json.loads((ROOT / "frozen-references.json").read_text())["documents"]
    pending = [trial_id for trial_id in sorted(references) if not artifacts(trial_id)["completed"].exists()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_one, trial_id, references[trial_id], args, protocol["prompt_hashes"]): trial_id for trial_id in pending}
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            trial_id = futures[future]; record = future.result(); error = record["runner"].get("error")
            print(f"{number}/{len(pending)} {trial_id} {'ok' if not error else error['type']}", flush=True)
    records = [json.loads(path.read_text()) for path in sorted((ROOT / "development/raw/completed").glob("*.json"))]
    if len(records) != 4: raise RuntimeError(f"cannot freeze: {len(records)}/4 completed")
    result_dir = ROOT / "development/raw/results"; atomic_bytes(result_dir / "trials-unscored.jsonl",
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records).encode())
    atomic_json(result_dir / "execution-freeze.json", {"arm": "raw", "scheduled": 4, "completed": 4,
        "responses_not_inspected_before_freeze": True,
        "trace_hashes": {row["trial_id"]: row["runner"]["trace_sha256"] for row in records},
        "runner_errors": sum(bool(row["runner"].get("error")) for row in records),
        "timeouts": sum(row["runner"]["timed_out"] for row in records), "direct_api_used": False})
    print("froze four Arm A raw-text trials")


if __name__ == "__main__": main()
