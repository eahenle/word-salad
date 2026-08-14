#!/usr/bin/env python3
"""Behavior-first Sol-xhigh fixed-versus-jitter anchor analysis."""

from __future__ import annotations

import json
import math
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


def main() -> None:
    root = Path(__file__).resolve().parent
    freeze = json.loads((root / "results" / "anchor-freeze.json").read_text())
    records = [
        json.loads(line) for line in (root / "results" / "anchor-trials-auto-scored.jsonl").read_text().splitlines()
        if line.strip()
    ]
    groups = defaultdict(list)
    for record in records:
        groups[record["carrier"]].append(record)
    summary = []
    for carrier in ("fixed", "jitter", "all-shuffled"):
        group = groups[carrier]
        expected = sum(record["semantic_success"] for record in group)
        target = sum(record["observed_answer_identity"] in {"A", "B"} for record in group)
        completed = sum(record["completed_response"] for record in group)
        low, high = wilson(expected, len(group))
        summary.append({
            "carrier": carrier,
            "scheduled": len(group),
            "completed": completed,
            "timeouts": sum(record["runner"]["timed_out"] for record in group),
            "expected_answers": expected,
            "target_answers": target,
            "expected_rate": expected / len(group),
            "ci_low": low,
            "ci_high": high,
        })
    pair_rows = []
    for carrier in ("fixed", "jitter"):
        indexed = {
            (record["seed"], record["payload_identity"]): record
            for record in groups[carrier]
        }
        pairs = [(indexed[(seed, "A")], indexed[(seed, "B")]) for seed in range(1, 11)]
        both = sum(a["semantic_success"] and b["semantic_success"] for a, b in pairs)
        low, high = wilson(both, len(pairs))
        pair_rows.append({
            "carrier": carrier,
            "pairs": len(pairs),
            "both_expected": both,
            "paired_rate": both / len(pairs),
            "ci_low": low,
            "ci_high": high,
        })
    fixed = next(row for row in pair_rows if row["carrier"] == "fixed")
    jitter = next(row for row in pair_rows if row["carrier"] == "jitter")
    result = {
        "cohort_freeze_sha256": __import__("hashlib").sha256(
            (root / "results" / "anchor-freeze.json").read_bytes()
        ).hexdigest(),
        "behavior_scored_before_trace_analysis": True,
        "summary": summary,
        "paired": pair_rows,
        "paired_jitter_penalty": fixed["paired_rate"] - jitter["paired_rate"],
        "manipulation_scientifically_informative": True,
        "decision": "proceed_to_common_screening_matrix",
        "trace_strategy_not_used_in_decision": True,
        "direct_api_calls": 0,
    }
    (root / "results" / "anchor-behavior.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        "# Sol-xhigh jitter anchor", "",
        "Behavior was scored after the cohort freeze and before trace strategy analysis.", "",
        "| carrier | scheduled | completed | timeouts | expected | target A/B |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary:
        lines.append(
            f"| {row['carrier']} | {row['scheduled']} | {row['completed']} | "
            f"{row['timeouts']} | {row['expected_answers']} | {row['target_answers']} |"
        )
    lines += ["", "| carrier | pairs | both expected | paired rate [95% Wilson CI] |",
              "| --- | ---: | ---: | --- |"]
    for row in pair_rows:
        lines.append(
            f"| {row['carrier']} | {row['pairs']} | {row['both_expected']} | "
            f"{row['paired_rate']:.1%} [{row['ci_low']:.1%}, {row['ci_high']:.1%}] |"
        )
    lines += ["", f"Paired jitter penalty: {result['paired_jitter_penalty']:.1%}.", "",
              "The manipulation is retained for the common matrix. This is a staged",
              "screening decision, not a final mechanistic conclusion.", ""]
    (root / "results" / "anchor-analysis.md").write_text("\n".join(lines))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
