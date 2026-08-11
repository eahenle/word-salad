#!/usr/bin/env python3
"""Run fresh blind Codex subjects and record verbatim final responses."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import tempfile
import time
from pathlib import Path

from generate import GENERATOR_VERSION, generate_trial


PLANNED_LANES = {1, 2, 4, 8, 16, 32}


def _parse_seed_spec(value: str) -> list[int]:
    if ":" in value:
        first, last = (int(part) for part in value.split(":", 1))
        if last < first:
            raise argparse.ArgumentTypeError("seed range must be ascending")
        return list(range(first, last + 1))
    return [int(part.strip()) for part in value.split(",")]


def _parse_events(
    stdout: str,
) -> tuple[str | None, dict | None, str | None, list[str]]:
    response = None
    usage = None
    thread_id = None
    non_json_lines = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            non_json_lines.append(line)
            continue
        if event.get("type") == "thread.started":
            thread_id = event.get("thread_id")
        elif event.get("type") == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                response = item.get("text", "")
        elif event.get("type") == "turn.completed":
            usage = event.get("usage")
    return response, usage, thread_id, non_json_lines


def _run_subject(task: dict, args: argparse.Namespace) -> tuple[int, dict]:
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="q.") as cwd:
        command = [
            args.codex,
            "-m",
            args.model,
            "-c",
            f'model_reasoning_effort="{args.reasoning}"',
            "-s",
            "read-only",
            "-a",
            "never",
            "-C",
            cwd,
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--strict-config",
            "--skip-git-repo-check",
            "-",
        ]
        try:
            completed = subprocess.run(
                command,
                input=task["prompt"],
                text=True,
                capture_output=True,
                timeout=args.timeout,
                check=False,
            )
            response, usage, thread_id, non_json_lines = _parse_events(completed.stdout)
            error = None
            if completed.returncode != 0 or response is None:
                error = {
                    "returncode": completed.returncode,
                    "stderr": completed.stderr,
                    "stdout": completed.stdout,
                }
                response = response or ""
        except subprocess.TimeoutExpired as exc:
            response = ""
            usage = None
            thread_id = None
            non_json_lines = []
            error = {
                "type": "timeout",
                "timeout_seconds": args.timeout,
                "stdout": exc.stdout,
                "stderr": exc.stderr,
            }
        except Exception as exc:  # preserve unexpected infrastructure failures
            response = ""
            usage = None
            thread_id = None
            non_json_lines = []
            error = {"type": "exception", "message": repr(exc)}

    record = {
        "trial_id": task["trial_id"],
        "condition": task["condition"],
        "lanes": task["lanes"],
        "seed": task["seed"],
        "signal_phase": task["metadata"]["signal_phase"],
        "model": args.model,
        "reasoning": args.reasoning,
        "prompt_words": task["metadata"]["prompt_words"],
        "response": response,
        "exact_success": None,
        "semantic_success": None,
        "encoding_discovered": None,
        "classification": None,
        "notes": "",
        "runner": {
            "method": "codex_exec_ephemeral",
            "thread_id": thread_id,
            "usage": usage,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "error": error,
            "non_json_stdout": non_json_lines,
        },
    }
    return task["index"], record


def _build_tasks(args: argparse.Namespace, payload: str) -> list[dict]:
    tasks = []
    for condition in args.conditions:
        for lanes in args.lanes:
            for seed in args.seeds:
                generated = generate_trial(
                    payload,
                    condition=condition,
                    lanes=lanes,
                    seed=seed,
                    corruption_fraction=args.corruption_fraction,
                )
                index = len(tasks) + 1
                tasks.append(
                    {
                        "index": index,
                        "neutral_id": f"q{index:04d}",
                        "trial_id": f"{condition}_N{lanes}_seed{seed:03d}",
                        "condition": condition,
                        "lanes": lanes,
                        "seed": seed,
                        "prompt": generated.prompt,
                        "metadata": generated.metadata,
                    }
                )
    return tasks


def _codex_version(executable: str) -> str | None:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    return completed.stdout.strip().rsplit(maxsplit=1)[-1]


def _write_outputs(tasks: list[dict], records: dict[int, dict], args: argparse.Namespace) -> None:
    if args.output.exists():
        raise FileExistsError(
            f"refusing to replace existing output directory: {args.output}"
        )
    prompt_dir = args.output / "prompts"
    prompt_dir.mkdir(parents=True)
    with (args.output / "trials-unscored.jsonl").open("w", encoding="utf-8") as trials, (
        args.output / "metadata.jsonl"
    ).open("w", encoding="utf-8") as metadata:
        for task in tasks:
            prompt_name = f"{task['neutral_id']}.txt"
            (prompt_dir / prompt_name).write_text(task["prompt"], encoding="utf-8")
            record = records[task["index"]]
            record["prompt_file"] = f"prompts/{prompt_name}"
            trials.write(json.dumps(record, ensure_ascii=False) + "\n")
            metadata.write(
                json.dumps(
                    {
                        "trial_id": task["trial_id"],
                        "neutral_id": task["neutral_id"],
                        **task["metadata"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    errors = sum(record["runner"]["error"] is not None for record in records.values())
    lane_set = set(args.lanes)
    deferred_lanes = sorted(PLANNED_LANES - lane_set) if lane_set <= PLANNED_LANES else []
    notes = []
    if deferred_lanes:
        notes.append(
            "Planned lane counts deferred from this run: "
            + ", ".join(str(lane) for lane in deferred_lanes)
            + "."
        )
    manifest = {
        "trials": len(records),
        "errors": errors,
        "completed_responses": sum(bool(record["response"]) for record in records.values()),
        "model": args.model,
        "reasoning": args.reasoning,
        "codex_cli": _codex_version(args.codex),
        "conditions": args.conditions,
        "lane_counts_run": args.lanes,
        "lane_counts_deferred": deferred_lanes,
        "payload_words": tasks[0]["metadata"]["payload_words"] if tasks else 0,
        "seeds": args.seeds,
        "workers": args.workers,
        "timeout_seconds": args.timeout,
        "generator_version": GENERATOR_VERSION,
        "answer_key_stored_in_source": False,
        "notes": notes,
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def _parser() -> argparse.ArgumentParser:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, default=here / "payload.txt")
    parser.add_argument("--output", type=Path, default=here / "run-output")
    parser.add_argument("--lanes", type=int, nargs="+", default=[1, 2, 4, 8, 16, 32])
    parser.add_argument("--seeds", type=_parse_seed_spec, default=list(range(1, 11)))
    parser.add_argument(
        "--conditions", nargs="+", default=["signal", "all_shuffled"]
    )
    parser.add_argument("--corruption-fraction", type=float, default=0.0)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning", default="xhigh")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--codex", default="codex")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if isinstance(args.seeds, list) and args.seeds and isinstance(args.seeds[0], list):
        args.seeds = [seed for group in args.seeds for seed in group]
    if args.workers < 1:
        raise ValueError("workers must be positive")
    if args.output.exists():
        raise FileExistsError(
            f"refusing to replace existing output directory: {args.output}"
        )
    payload = args.payload.read_text(encoding="utf-8").strip()
    tasks = _build_tasks(args, payload)
    records: dict[int, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_run_subject, task, args) for task in tasks]
        for completed_count, future in enumerate(
            concurrent.futures.as_completed(futures), start=1
        ):
            index, record = future.result()
            records[index] = record
            status = "ok" if record["runner"]["error"] is None else "error"
            print(
                f"{completed_count}/{len(tasks)} {record['trial_id']} {status}",
                flush=True,
            )
    _write_outputs(tasks, records, args)


if __name__ == "__main__":
    main()
