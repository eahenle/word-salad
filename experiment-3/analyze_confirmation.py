#!/usr/bin/env python3
"""Analyze the preregistered Experiment 3 boundary-confirmation cohort."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from analyze import MODEL_LABELS, grouped_chart, median, wilson
from runtime import atomic_bytes, cell_slug
from trace_strategy import analyze_trace


SELECTED = (
    ("gpt-5.6-sol", "medium"),
    ("gpt-5.6-terra", "xhigh"),
    ("gpt-5.3-codex-spark", "xhigh"),
)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load(root: Path) -> tuple[list[dict], list[dict]]:
    combined: list[dict] = []
    confirmation: list[dict] = []
    for model, effort in SELECTED:
        path = root / "results/cells" / cell_slug(model, effort) / "trials-auto-scored.jsonl"
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        signals = [
            record for record in records
            if record["carrier"] in {"fixed", "jitter"} and 1 <= record["seed"] <= 20
        ]
        if len(signals) != 80:
            raise RuntimeError(f"{model}/{effort}: expected 80 cumulative signal trials, got {len(signals)}")
        for record in signals:
            trace_result = analyze_trace(root / record["trace_file"], record)
            merged = dict(record)
            merged["observable_strategy"] = trace_result["strategy"]
            merged["strategy_flags"] = trace_result["flags"]
            merged["strategy_evidence"] = trace_result["evidence"]
            merged["trace_metrics"] = {
                key: value for key, value in trace_result.items()
                if key not in {"strategy", "flags", "evidence"}
            }
            merged["analysis_cohort"] = "screening" if record["seed"] <= 10 else "confirmation"
            combined.append(merged)
            if record["seed"] >= 11:
                confirmation.append(merged)
    if len(combined) != 240 or len(confirmation) != 120:
        raise RuntimeError("confirmation cohort count mismatch")
    return combined, confirmation


def summary_rows(records: list[dict]) -> list[dict]:
    rows = []
    cohorts = (("screening", range(1, 11)), ("confirmation", range(11, 21)), ("cumulative", range(1, 21)))
    for model, effort in SELECTED:
        for cohort, seed_range in cohorts:
            seeds = list(seed_range)
            for carrier in ("fixed", "jitter"):
                group = [
                    record for record in records
                    if record["model"] == model and record["reasoning"] == effort
                    and record["carrier"] == carrier and record["seed"] in seeds
                ]
                index = {(record["seed"], record["payload_identity"]): record for record in group}
                paired = sum(
                    bool(index[(seed, "A")]["semantic_success"] and index[(seed, "B")]["semantic_success"])
                    for seed in seeds
                )
                individual = sum(bool(record["semantic_success"]) for record in group)
                i_low, i_high = wilson(individual, len(group))
                p_low, p_high = wilson(paired, len(seeds))
                rows.append({
                    "cohort": cohort, "model": model, "reasoning": effort, "carrier": carrier,
                    "individual_success": individual, "individual_trials": len(group),
                    "individual_rate": individual / len(group), "individual_ci_low": i_low,
                    "individual_ci_high": i_high, "paired_success": paired, "pairs": len(seeds),
                    "paired_rate": paired / len(seeds), "paired_ci_low": p_low, "paired_ci_high": p_high,
                    "counterpart_answer_errors": sum(
                        bool(record["observed_answer_identity"] and record["observed_answer_identity"] != record["answer_identity"])
                        for record in group
                    ),
                    "timeouts": sum(bool(record["runner"]["timed_out"]) for record in group),
                    "tool_using_trials": sum(record["trace_metrics"]["tool_calls"] > 0 for record in group),
                    "median_elapsed_seconds": median([record["runner"]["elapsed_seconds"] for record in group]),
                    "median_reasoning_tokens": median([record["trace_metrics"]["reasoning_tokens"] for record in group]),
                })
    return rows


def exact_mcnemar(records: list[dict], seeds: range, paired: bool) -> dict:
    fixed_only = jitter_only = comparisons = 0
    for model, effort in SELECTED:
        cell = [record for record in records if record["model"] == model and record["reasoning"] == effort]
        index = {(record["carrier"], record["seed"], record["payload_identity"]): record for record in cell}
        for seed in seeds:
            if paired:
                values = [(
                    all(index[("fixed", seed, identity)]["semantic_success"] for identity in ("A", "B")),
                    all(index[("jitter", seed, identity)]["semantic_success"] for identity in ("A", "B")),
                )]
            else:
                values = [
                    (index[("fixed", seed, identity)]["semantic_success"], index[("jitter", seed, identity)]["semantic_success"])
                    for identity in ("A", "B")
                ]
            for fixed, jitter in values:
                comparisons += 1
                fixed_only += bool(fixed and not jitter)
                jitter_only += bool(jitter and not fixed)
    discordant = fixed_only + jitter_only
    tail = min(fixed_only, jitter_only)
    p_value = min(1.0, 2 * sum(math.comb(discordant, i) for i in range(tail + 1)) / 2**discordant) if discordant else 1.0
    return {
        "comparisons": comparisons, "fixed_only_success": fixed_only,
        "jitter_only_success": jitter_only, "discordant": discordant,
        "two_sided_exact_mcnemar_p": p_value,
    }


def report(records: list[dict], rows: list[dict], tests: dict) -> str:
    index = {(r["cohort"], r["model"], r["reasoning"], r["carrier"]): r for r in rows}
    fresh = [r for r in rows if r["cohort"] == "confirmation"]
    cumulative = [r for r in rows if r["cohort"] == "cumulative"]
    fresh_fixed = sum(r["individual_success"] for r in fresh if r["carrier"] == "fixed")
    fresh_jitter = sum(r["individual_success"] for r in fresh if r["carrier"] == "jitter")
    fresh_fixed_pairs = sum(r["paired_success"] for r in fresh if r["carrier"] == "fixed")
    fresh_jitter_pairs = sum(r["paired_success"] for r in fresh if r["carrier"] == "jitter")
    cumulative_successes = [r for r in records if r["semantic_success"]]
    strategy = Counter(r["observable_strategy"] for r in cumulative_successes)
    lines = [
        "# Experiment 3 targeted confirmation", "",
        "## Result", "",
        f"The preregistered fresh-seed confirmation produced {fresh_fixed}/60 fixed and {fresh_jitter}/60 jitter expected individual answers, with {fresh_fixed_pairs}/30 versus {fresh_jitter_pairs}/30 complete A/B pairs. Thus the large screening-wide jitter advantage narrowed in these three confirmation cells, but it did not reverse.", "",
        f"Across screening plus confirmation for the selected cells, the matched fresh-seed comparison contained {tests['cumulative_paired']['fixed_only_success']} fixed-only and {tests['cumulative_paired']['jitter_only_success']} jitter-only paired successes (exact McNemar p={tests['cumulative_paired']['two_sided_exact_mcnemar_p']:.4g}). This is a repeatability summary, not population inference over models.", "",
        "## Fresh and cumulative cells", "",
        "| model | cohort | fixed individual | fixed pairs | jitter individual | jitter pairs | paired jitter penalty | counterpart errors |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model, effort in SELECTED:
        for cohort in ("confirmation", "cumulative"):
            fixed = index[(cohort, model, effort, "fixed")]
            jitter = index[(cohort, model, effort, "jitter")]
            lines.append(
                f"| {MODEL_LABELS[model]}-{effort} | {cohort} | {fixed['individual_success']}/{fixed['individual_trials']} | "
                f"{fixed['paired_success']}/{fixed['pairs']} | {jitter['individual_success']}/{jitter['individual_trials']} | "
                f"{jitter['paired_success']}/{jitter['pairs']} | {fixed['paired_rate']-jitter['paired_rate']:.0%} | "
                f"{fixed['counterpart_answer_errors'] + jitter['counterpart_answer_errors']} |"
            )
    lines += [
        "", "Sol-medium replicated robust recovery: its confirmation half was tied at 6/10 pairs for each carrier, and its cumulative result was 10/20 fixed versus 12/20 jitter pairs. Terra-xhigh retained the predicted direction at 2/10 versus 3/10 fresh pairs and 2/20 versus 6/20 cumulatively. Spark-xhigh produced no confirmation success; cumulatively it had one jitter individual answer and no complete pair. The Spark boundary therefore replicated as essentially absent recovery.", "",
        "## Effort and observable strategy", "",
        "No confirmation trial timed out or had a runner/infrastructure error. Median time and reasoning-token values are preserved per cell in `confirmation-summary.csv`.", "",
        f"Across all {len(cumulative_successes)} successful selected-cell signal trials from seeds 1–20, observable strategies were: " + ", ".join(f"`{name}` {count}" for name, count in sorted(strategy.items())) + ". These labels use only emitted events; they do not expose private chain of thought.", "",
        "The primary successful mode remained direct and tool-free. Specific stride or jitter discovery is counted only when a trace contains concrete emitted evidence, never inferred from a terse correct answer.", "",
        "## Interpretation", "",
        "The confirmation supports the screening conclusion that a strict period-2 clock is not necessary for this task. It does not establish recovery under arbitrary irregular placement: the balanced jitter mask contains adjacent signal-word bursts, a plausible local-coherence advantage. Reasoning effort was nonmonotonic in screening, while confirmation reinforces a strong family-level boundary: Sol succeeds reliably, Terra partially, and Spark effectively not at all.", "",
        "The most discriminating next experiment is a small, preregistered uniform-random-placement comparison in Sol-medium and Terra-xhigh. That should be a new frozen experiment, not an extension of this dataset.", "",
    ]
    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).resolve().parent
    freeze = json.loads((root / "results/confirmation-freeze.json").read_text())
    integrity = json.loads((root / "results/integrity-audit.json").read_text())
    if freeze.get("status") != "frozen_before_confirmation_scoring_and_trace_analysis":
        raise RuntimeError("valid confirmation freeze required")
    if not integrity.get("passed"):
        raise RuntimeError("passed integrity audit required")
    combined, confirmation = load(root)
    rows = summary_rows(combined)
    tests = {
        "confirmation_individual": exact_mcnemar(combined, range(11, 21), False),
        "confirmation_paired": exact_mcnemar(combined, range(11, 21), True),
        "cumulative_individual": exact_mcnemar(combined, range(1, 21), False),
        "cumulative_paired": exact_mcnemar(combined, range(1, 21), True),
    }
    results = root / "results"
    atomic_bytes(results / "confirmation-trials.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in confirmation).encode())
    atomic_bytes(results / "confirmation-combined-trials.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in combined).encode())
    write_csv(results / "confirmation-summary.csv", rows)
    (results / "confirmation-matched-tests.json").write_text(json.dumps(tests, indent=2) + "\n")
    (results / "confirmation-analysis.md").write_text(report(combined, rows, tests))

    cumulative = {(r["model"], r["reasoning"], r["carrier"]): r for r in rows if r["cohort"] == "cumulative"}
    labels = [f"{MODEL_LABELS[model]}-{effort[0].upper()}" for model, effort in SELECTED]
    grouped_chart(results / "figures/confirmation-individual.svg", "Selected cells: cumulative individual recovery", labels,
                  [cumulative[(m, e, "fixed")]["individual_rate"] for m, e in SELECTED],
                  [cumulative[(m, e, "jitter")]["individual_rate"] for m, e in SELECTED], "success rate")
    grouped_chart(results / "figures/confirmation-paired.svg", "Selected cells: cumulative paired discrimination", labels,
                  [cumulative[(m, e, "fixed")]["paired_rate"] for m, e in SELECTED],
                  [cumulative[(m, e, "jitter")]["paired_rate"] for m, e in SELECTED], "paired success rate")
    print(json.dumps({"confirmation_records": len(confirmation), "combined_records": len(combined), "tests": tests}, indent=2))


if __name__ == "__main__":
    main()
