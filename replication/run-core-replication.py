#!/usr/bin/env python3
"""Run frozen prompts through any stdin-to-one-response model command."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def text_value(value) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "execution-manifest.json")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "external-results")
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--max-trials", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("model_command", nargs=argparse.REMAINDER, help="command after --; prompt is supplied on stdin")
    args = parser.parse_args()
    command = args.model_command[1:] if args.model_command[:1] == ["--"] else args.model_command
    manifest = json.loads(args.manifest.read_text())
    trials = manifest["trials"][: args.max_trials]
    validated = []
    for trial in trials:
        prompt_path = ROOT / trial["prompt_file"]
        data = prompt_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != trial["prompt_sha256"]:
            raise SystemExit(f"prompt hash mismatch: {trial['trial_id']}")
        if len(data.decode("utf-8").split()) != trial["prompt_words"]:
            raise SystemExit(f"prompt word-count mismatch: {trial['trial_id']}")
        validated.append(trial["trial_id"])
    if args.dry_run:
        print(json.dumps({"status": "validated", "trials": len(validated)}, indent=2))
        return
    if not command:
        raise SystemExit("provide a model command after --, or use --dry-run")
    args.results_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for trial in trials:
        result_path = args.results_dir / f"{trial['trial_id']}.json"
        if result_path.exists():
            records.append(json.loads(result_path.read_text()))
            continue
        prompt = (ROOT / trial["prompt_file"]).read_text()
        started = time.monotonic()
        try:
            completed = subprocess.run(command, input=prompt, text=True, capture_output=True, timeout=args.timeout_seconds, shell=False)
            record = {**trial, "command_argv": command, "response": completed.stdout, "stderr": completed.stderr, "exit_status": completed.returncode, "timed_out": False, "elapsed_seconds": time.monotonic() - started}
        except subprocess.TimeoutExpired as error:
            record = {**trial, "command_argv": command, "response": text_value(error.stdout), "stderr": text_value(error.stderr), "exit_status": None, "timed_out": True, "elapsed_seconds": time.monotonic() - started}
        result_path.write_text(json.dumps(record, indent=2) + "\n")
        records.append(record)
    with (args.results_dir / "responses.jsonl").open("w") as stream:
        for record in records:
            stream.write(json.dumps(record, separators=(",", ":")) + "\n")
    print(json.dumps({"completed_records": len(records), "results_dir": str(args.results_dir)}, indent=2))


if __name__ == "__main__":
    main()
