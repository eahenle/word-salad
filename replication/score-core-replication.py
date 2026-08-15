#!/usr/bin/env python3
"""Score answer identity and paired discrimination for an external replication."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OBJECTS = ("brass key", "silver coin", "glass marble")


def assignments(text: str) -> dict[str, str]:
    found = {}
    for object_name in OBJECTS:
        match = re.search(rf"{re.escape(object_name)}\s*=\s*(red|blue|green)\b", text, re.IGNORECASE)
        if match:
            found[object_name] = match.group(1).lower()
    return found


def parse_answer(text: str) -> str | None:
    observed = assignments(text)
    answer_a = {"brass key": "green", "silver coin": "blue", "glass marble": "green"}
    answer_b = {"brass key": "green", "silver coin": "red", "glass marble": "green"}
    return "A" if observed == answer_a else "B" if observed == answer_b else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_dir", type=Path)
    parser.add_argument("--key", type=Path, default=ROOT / "scoring-key.json")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or args.results_dir / "scored"
    output.mkdir(parents=True, exist_ok=True)
    key = {row["trial_id"]: row for row in json.loads(args.key.read_text())["trials"]}
    records = []
    for line in (args.results_dir / "responses.jsonl").read_text().splitlines():
        run = json.loads(line)
        expected = key[run["trial_id"]]
        observed = parse_answer(run.get("response", ""))
        records.append({**expected, "observed_identity": observed, "expected_success": expected["identity"] is not None and observed == expected["identity"], "control_target": expected["condition"] == "all_shuffled" and observed is not None, "timed_out": bool(run.get("timed_out")), "exit_status": run.get("exit_status")})
    with (output / "scored-trials.jsonl").open("w") as stream:
        for record in records:
            stream.write(json.dumps(record, separators=(",", ":")) + "\n")
    groups = defaultdict(list)
    for record in records:
        groups[(record["study"], record["condition"])].append(record)
    summaries = []
    for (study, condition), group in sorted(groups.items()):
        summaries.append({"study": study, "condition": condition, "trials": len(group), "expected_success": sum(r["expected_success"] for r in group), "control_targets": sum(r["control_target"] for r in group), "timeouts": sum(r["timed_out"] for r in group)})
    with (output / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader(); writer.writerows(summaries)
    by_pair = defaultdict(dict)
    for record in records:
        if record["condition"] == "signal":
            by_pair[(record["study"], record["seed"])][record["identity"]] = record["expected_success"]
    pairs = [{"study": study, "seed": seed, "complete_pair": values.get("A", False) and values.get("B", False), "A_present": "A" in values, "B_present": "B" in values} for (study, seed), values in sorted(by_pair.items())]
    (output / "paired-results.json").write_text(json.dumps(pairs, indent=2) + "\n")
    final = {"records": len(records), "observed_identity_counts": Counter(r["observed_identity"] or "other" for r in records), "complete_pairs": sum(r["complete_pair"] for r in pairs), "pair_denominator": sum(r["A_present"] and r["B_present"] for r in pairs), "control_targets": sum(r["control_target"] for r in records)}
    (output / "summary.json").write_text(json.dumps(final, indent=2) + "\n")
    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    main()
