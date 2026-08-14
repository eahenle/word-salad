#!/usr/bin/env python3
"""Probe the two exact Experiment 4A Codex cells without substitution."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from runtime import CELLS, IMAGE, atomic_json, cell_slug, run_subject


def classify(run: dict) -> str:
    text = ("\n".join(run["parsed"]["error_messages"]) + "\n" + run["raw_stderr"].decode(errors="replace")).lower()
    if run["error"] is None and run["parsed"]["response"]:
        return "supported"
    if re.search(r"reasoning.{0,80}(unsupported|not supported|invalid)", text):
        return "unsupported_reasoning_effort"
    if "model" in text and any(term in text for term in ("not found", "does not exist", "unknown", "unavailable", "not supported")):
        return "model_unavailable"
    if "capacity" in text or "temporarily unavailable" in text or "usage limit" in text:
        return "temporarily_capacity_limited"
    return "other_failure"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--auth", type=Path, required=True)
    parser.add_argument("--image", default=IMAGE)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    isolation = json.loads((args.root / "uniform/results/isolation-validation.json").read_text())
    if not isolation.get("passed") or isolation.get("image") != args.image:
        raise RuntimeError("passed image-matched isolation validation required")
    output = []
    for model, effort in CELLS:
        slug = cell_slug(model, effort)
        directory = args.root / "uniform/capability-probes" / slug
        record_path = directory / "result.json"
        if record_path.exists():
            output.append(json.loads(record_path.read_text()))
            continue
        run = run_subject(prompt="Reply with exactly OK.", auth=args.auth, model=model, effort=effort,
                          timeout=args.timeout, image=args.image, name_prefix="word-salad-q4-capability")
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "trace.jsonl").write_bytes(run["raw_stdout"])
        (directory / "stderr.txt").write_bytes(run["raw_stderr"])
        record = {"model": model, "reasoning": effort, "status": classify(run),
                  "response": run["parsed"]["response"] or "", "thread_id": run["parsed"]["thread_id"],
                  "usage": run["parsed"]["usage"], "elapsed_seconds": run["elapsed_seconds"],
                  "exit_status": run["exit_status"], "timed_out": run["timed_out"], "error": run["error"],
                  "error_messages": run["parsed"]["error_messages"],
                  "trace_file": f"uniform/capability-probes/{slug}/trace.jsonl",
                  "stderr_file": f"uniform/capability-probes/{slug}/stderr.txt",
                  "trace_sha256": hashlib.sha256(run["raw_stdout"]).hexdigest(),
                  "stderr_sha256": hashlib.sha256(run["raw_stderr"]).hexdigest(),
                  "substitution_performed": False}
        atomic_json(record_path, record)
        output.append(record)
        print(f"{model} {effort}: {record['status']}", flush=True)
    atomic_json(args.root / "uniform/results/capability-probe.json", {
        "image": args.image, "requested_cells": len(CELLS), "probed_cells": len(output),
        "substitution_performed": False, "cells": output,
    })
    print(json.dumps({f"{r['model']}:{r['reasoning']}": r["status"] for r in output}, indent=2))


if __name__ == "__main__":
    main()
