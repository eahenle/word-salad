#!/usr/bin/env python3
"""Analyze answer identity, paired discrimination, controls, and effort."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if not trials:
        return 0.0, 0.0
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def median(values: list[int | float | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return statistics.median(clean) if clean else None


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def answer_matrix(records: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        groups[(record["arm"], record["condition"], record["lanes"],
                record.get("payload_identity") or "none")].append(record)
    rows = []
    for key in sorted(groups):
        group = groups[key]
        successes = sum(bool(record["semantic_success"]) for record in group)
        low, high = wilson(successes, len(group))
        rows.append({
            "arm": key[0], "condition": key[1], "lanes": key[2],
            "stimulus_identity": key[3], "trials": len(group),
            "completed_responses": sum(bool(record["completed_response"]) for record in group),
            "answer_A": sum(record["observed_answer_identity"] == "A" for record in group),
            "answer_B": sum(record["observed_answer_identity"] == "B" for record in group),
            "other_or_no_answer": sum(record["observed_answer_identity"] is None for record in group),
            "expected_success": successes, "expected_success_rate": successes / len(group),
            "success_ci_low": low, "success_ci_high": high,
        })
    return rows


def paired(records: list[dict]) -> list[dict]:
    indexed = {
        (record["arm"], record["condition"], record["lanes"], record["seed"],
         record.get("payload_identity")): record
        for record in records if record["condition"] in {"clean", "signal"}
    }
    groups: dict[tuple, list[tuple[dict, dict]]] = defaultdict(list)
    coordinates = {(key[0], key[1], key[2], key[3]) for key in indexed}
    for arm, condition, lanes, seed in sorted(coordinates):
        a = indexed.get((arm, condition, lanes, seed, "A"))
        b = indexed.get((arm, condition, lanes, seed, "B"))
        if a and b:
            groups[(arm, condition, lanes)].append((a, b))
    rows = []
    for key in sorted(groups):
        pairs = groups[key]
        discriminating = sum(
            a["observed_answer_identity"] == "A" and b["observed_answer_identity"] == "B"
            for a, b in pairs
        )
        low, high = wilson(discriminating, len(pairs))
        rows.append({
            "arm": key[0], "condition": key[1], "lanes": key[2],
            "paired_seeds": len(pairs), "ordered_lane_discriminating_pairs": discriminating,
            "discriminating_rate": discriminating / len(pairs),
            "discriminating_ci_low": low, "discriminating_ci_high": high,
            "both_expected": sum(a["semantic_success"] and b["semantic_success"] for a, b in pairs),
            "A_expected_B_not": sum(a["semantic_success"] and not b["semantic_success"] for a, b in pairs),
            "B_expected_A_not": sum(b["semantic_success"] and not a["semantic_success"] for a, b in pairs),
            "neither_expected": sum(not a["semantic_success"] and not b["semantic_success"] for a, b in pairs),
            "same_A_answer": sum(
                a["observed_answer_identity"] == b["observed_answer_identity"] == "A" for a, b in pairs
            ),
            "same_B_answer": sum(
                a["observed_answer_identity"] == b["observed_answer_identity"] == "B" for a, b in pairs
            ),
        })
    return rows


def effort(records: list[dict], traces: dict[str, dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        groups[(record["arm"], record["condition"], record["lanes"])].append(record)
    rows = []
    for key in sorted(groups):
        group = groups[key]
        metrics = [traces[record["neutral_id"]] for record in group]
        rows.append({
            "arm": key[0], "condition": key[1], "lanes": key[2], "trials": len(group),
            "timeouts": sum(record["runner"]["timed_out"] for record in group),
            "tool_using_trials": sum(metric["tool_calls"] > 0 for metric in metrics),
            "median_elapsed_seconds": median([record["runner"]["elapsed_seconds"] for record in group]),
            "median_input_tokens": median([metric["input_tokens"] for metric in metrics]),
            "median_output_tokens": median([metric["output_tokens"] for metric in metrics]),
            "median_reasoning_tokens": median([metric["reasoning_tokens"] for metric in metrics]),
            "median_tool_calls": median([metric["tool_calls"] for metric in metrics]),
            "median_trace_bytes": median([metric["trace_bytes"] for metric in metrics]),
        })
    return rows


def report(answer_rows: list[dict], pair_rows: list[dict], effort_rows: list[dict]) -> str:
    lines = [
        "# Experiment 2 analysis", "",
        "This report treats answer identity as the primary endpoint. A signal A trial is",
        "successful only when it produces answer A, and likewise for B. All-shuffled",
        "outputs are reported as answer bias rather than generic correctness.", "",
        "## Answer identity", "",
        "| arm | condition | N | stimulus | trials | A | B | other | expected |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in answer_rows:
        lines.append(
            f"| {row['arm']} | {row['condition']} | {row['lanes']} | "
            f"{row['stimulus_identity']} | {row['trials']} | {row['answer_A']} | "
            f"{row['answer_B']} | {row['other_or_no_answer']} | {row['expected_success']} |"
        )
    lines += ["", "## Paired A/B discrimination", "",
              "| arm | condition | N | pairs | A→A and B→B | rate |",
              "| --- | --- | ---: | ---: | ---: | ---: |"]
    for row in pair_rows:
        lines.append(
            f"| {row['arm']} | {row['condition']} | {row['lanes']} | "
            f"{row['paired_seeds']} | {row['ordered_lane_discriminating_pairs']} | "
            f"{row['discriminating_rate']:.3f} |"
        )
    lines += ["", "## Computational effort", "",
              "| arm | condition | N | trials | timeouts | tool users | median seconds | median input | median reasoning |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in effort_rows:
        lines.append(
            f"| {row['arm']} | {row['condition']} | {row['lanes']} | {row['trials']} | "
            f"{row['timeouts']} | {row['tool_using_trials']} | {row['median_elapsed_seconds']:.1f} | "
            f"{row['median_input_tokens'] or 0:.0f} | {row['median_reasoning_tokens'] or 0:.0f} |"
        )
    lines += ["", "Behavioral correctness and observable trace strategy are separate outcomes.",
              "No claim about private internal reasoning is made.", ""]
    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--trials", type=Path)
    parser.add_argument("--traces", type=Path)
    args = parser.parse_args()
    trials_path = args.trials or args.root / "results" / "trials.jsonl"
    traces_path = args.traces or args.root / "results" / "trace-metrics.jsonl"
    records = [json.loads(line) for line in trials_path.read_text().splitlines() if line.strip()]
    traces = {
        row["neutral_id"]: row for row in (
            json.loads(line) for line in traces_path.read_text().splitlines() if line.strip()
        )
    }
    if set(traces) != {record["neutral_id"] for record in records}:
        raise ValueError("trial/trace ID sets differ")
    answer_rows, pair_rows = answer_matrix(records), paired(records)
    effort_rows = effort(records, traces)
    results = args.root / "results"
    write_csv(results / "answer-identity.csv", answer_rows)
    write_csv(results / "paired-discrimination.csv", pair_rows)
    write_csv(results / "effort-summary.csv", effort_rows)
    (results / "analysis.md").write_text(report(answer_rows, pair_rows, effort_rows))
    print(f"analyzed {len(records)} Experiment 2 trials")


if __name__ == "__main__":
    main()
