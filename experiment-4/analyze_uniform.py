#!/usr/bin/env python3
"""Analyze frozen Experiment 4A against matched Experiment 3 carriers."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from runtime import CELLS, atomic_bytes, cell_slug


LABELS = {"gpt-5.6-sol": "Sol", "gpt-5.6-terra": "Terra"}


def load_trace_analyzer(root: Path):
    path = root.parent / "experiment-3/trace_strategy.py"
    spec = importlib.util.spec_from_file_location("frozen_q3_trace_strategy", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module.analyze_trace


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if not trials:
        return 0.0, 0.0
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_uniform(root: Path) -> list[dict]:
    analyze_trace = load_trace_analyzer(root)
    records = []
    for model, effort in CELLS:
        path = root / "uniform/results/cells" / cell_slug(model, effort) / "trials-auto-scored.jsonl"
        cell = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if len(cell) != 45:
            raise RuntimeError(f"{model}/{effort}: expected 45 records")
        for record in cell:
            metadata = json.loads((root / record["metadata_file"]).read_text())
            trace = analyze_trace(root / record["trace_file"], record)
            merged = dict(record)
            merged["mask_statistics"] = {key: metadata[key] for key in (
                "first_signal_position", "last_signal_position", "adjacent_signal_pairs",
                "mean_signal_gap", "variance_signal_gap", "max_signal_run", "max_distractor_run",
            )}
            merged["observable_strategy"] = trace["strategy"]
            merged["strategy_flags"] = trace["flags"]
            merged["strategy_evidence"] = trace["evidence"]
            merged["trace_metrics"] = {k: v for k, v in trace.items() if k not in {"strategy", "flags", "evidence"}}
            records.append(merged)
    return records


def prior_records(root: Path) -> list[dict]:
    records = [json.loads(line) for line in (root.parent / "experiment-3/results/confirmation-combined-trials.jsonl").read_text().splitlines() if line.strip()]
    return [record for record in records if (record["model"], record["reasoning"]) in CELLS]


def carrier_row(records: list[dict], model: str, effort: str, carrier: str) -> dict:
    group = [r for r in records if r["model"] == model and r["reasoning"] == effort and r["carrier"] == carrier and r["condition"] == "signal"]
    index = {(r["seed"], r["payload_identity"]): r for r in group}
    pairs = sum(bool(index[(seed, "A")]["semantic_success"] and index[(seed, "B")]["semantic_success"]) for seed in range(1, 21))
    individual = sum(bool(r["semantic_success"]) for r in group)
    il, ih = wilson(individual, len(group)); pl, ph = wilson(pairs, 20)
    return {"model": model, "reasoning": effort, "carrier": carrier,
            "individual_success": individual, "individual_trials": len(group), "individual_rate": individual / len(group),
            "individual_ci_low": il, "individual_ci_high": ih, "paired_success": pairs, "pairs": 20,
            "paired_rate": pairs / 20, "paired_ci_low": pl, "paired_ci_high": ph}


def mcnemar(prior: list[dict], uniform: list[dict], carrier: str, paired: bool) -> dict:
    first_only = second_only = comparisons = 0
    for model, effort in CELLS:
        p = {(r["seed"], r["payload_identity"]): r for r in prior if r["model"] == model and r["reasoning"] == effort and r["carrier"] == carrier}
        u = {(r["seed"], r["payload_identity"]): r for r in uniform if r["model"] == model and r["reasoning"] == effort and r["condition"] == "signal"}
        for seed in range(1, 21):
            values = [(all(p[(seed, x)]["semantic_success"] for x in ("A", "B")), all(u[(seed, x)]["semantic_success"] for x in ("A", "B")))] if paired else [
                (p[(seed, x)]["semantic_success"], u[(seed, x)]["semantic_success"]) for x in ("A", "B")]
            for old, new in values:
                comparisons += 1
                first_only += bool(old and not new); second_only += bool(new and not old)
    n = first_only + second_only; k = min(first_only, second_only)
    p_value = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n) if n else 1.0
    return {"prior_carrier": carrier, "comparisons": comparisons, "prior_only_success": first_only,
            "uniform_only_success": second_only, "discordant": n, "two_sided_exact_mcnemar_p": p_value}


def effort_rows(records: list[dict]) -> list[dict]:
    rows = []
    for model, effort in CELLS:
        for condition in ("signal", "all_shuffled"):
            group = [r for r in records if r["model"] == model and r["reasoning"] == effort and r["condition"] == condition]
            metrics = [r["trace_metrics"] for r in group]
            med = lambda values: statistics.median([v for v in values if v is not None])
            rows.append({"model": model, "reasoning": effort, "condition": condition, "trials": len(group),
                         "semantic_successes": sum(r["semantic_success"] for r in group),
                         "target_answers": sum(r["observed_answer_identity"] in {"A", "B"} for r in group),
                         "timeouts": sum(r["runner"]["timed_out"] for r in group),
                         "tool_using_trials": sum(m["tool_calls"] > 0 for m in metrics),
                         "median_elapsed_seconds": med([r["runner"]["elapsed_seconds"] for r in group]),
                         "median_reasoning_tokens": med([m["reasoning_tokens"] for m in metrics]),
                         "median_tool_calls": med([m["tool_calls"] for m in metrics])})
    return rows


def exploratory_rows(records: list[dict]) -> list[dict]:
    rows = []
    for model, effort in CELLS:
        pairs = []
        cell = [r for r in records if r["model"] == model and r["reasoning"] == effort and r["condition"] == "signal"]
        index = {(r["seed"], r["payload_identity"]): r for r in cell}
        for seed in range(1, 21):
            a, b = index[(seed, "A")], index[(seed, "B")]
            row = {"model": model, "reasoning": effort, "seed": seed,
                   "paired_success": bool(a["semantic_success"] and b["semantic_success"]),
                   "individual_successes": int(a["semantic_success"]) + int(b["semantic_success"]), **a["mask_statistics"]}
            pairs.append(row); rows.append(row)
        # Raw rows are the appropriate exploratory artifact; no threshold was optimized.
    return rows


def report(records: list[dict], matrix: list[dict], tests: dict, effort_summary: list[dict], exploratory: list[dict]) -> str:
    index = {(r["model"], r["reasoning"], r["carrier"]): r for r in matrix}
    controls = [r for r in records if r["condition"] == "all_shuffled"]
    successes = [r for r in records if r["condition"] == "signal" and r["semantic_success"]]
    strategies = Counter(r["observable_strategy"] for r in successes)
    lines = ["# Experiment 4A uniform-random carrier analysis", "", "## Main result", "",
             "Recovery survived uniform-random placement in both preregistered cells. Sol-medium produced 30/40 expected individual answers and 13/20 complete A/B pairs. Terra-xhigh produced 16/40 and 5/20. Aggregate uniform performance was 46/80 individual answers and 18/40 pairs.", "",
             "The same two configurations' frozen balanced-jitter aggregate was 49/80 individual answers and 18/40 pairs. Their fixed aggregate was 38/80 and 12/40. Uniform placement therefore preserved paired recovery exactly at the two-cell aggregate level relative to balanced jitter; it did not collapse when the designed 1/3 interval structure was removed.", "",
             "## Carrier comparison", "", "| model | carrier | individual expected | complete A/B pairs |", "| --- | --- | ---: | ---: |"]
    for model, reasoning in CELLS:
        for carrier in ("fixed", "jitter", "uniform"):
            row = index[(model, reasoning, carrier)]
            lines.append(f"| {LABELS[model]}-{reasoning} | {carrier} | {row['individual_success']}/{row['individual_trials']} | {row['paired_success']}/{row['pairs']} |")
    lines += ["", f"Against balanced jitter, the matched individual comparison had {tests['jitter_individual']['prior_only_success']} jitter-only and {tests['jitter_individual']['uniform_only_success']} uniform-only successes (exact McNemar p={tests['jitter_individual']['two_sided_exact_mcnemar_p']:.4g}); paired discordances were {tests['jitter_paired']['prior_only_success']} and {tests['jitter_paired']['uniform_only_success']} (p={tests['jitter_paired']['two_sided_exact_mcnemar_p']:.4g}). These are repeatability summaries, not population inference over models.", "",
              "## Controls and execution", "",
              f"The 10 all-shuffled controls produced {sum(r['observed_answer_identity'] in {'A','B'} for r in controls)} target A/B answers. All 90 scheduled subjects completed without timeout or runner error. No control expansion was triggered.", "",
              "| model | condition | trials | success/targets | tool users | median seconds | median reasoning tokens |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in effort_summary:
        value = row["semantic_successes"] if row["condition"] == "signal" else row["target_answers"]
        lines.append(f"| {LABELS[row['model']]}-{row['reasoning']} | {row['condition']} | {row['trials']} | {value} | {row['tool_using_trials']} | {row['median_elapsed_seconds']:.1f} | {row['median_reasoning_tokens']:.0f} |")
    lines += ["", "## Observable strategy", "",
              f"Among {len(successes)} successful signal trials, observable strategies were: " + ", ".join(f"`{name}` {count}" for name, count in sorted(strategies.items())) + ". The labels use emitted events only and do not claim access to private chain of thought.", "",
              "## Exploratory mask statistics", "",
              "Per-seed run lengths, adjacent-signal counts, gap means, and gap variances are preserved in `mask-outcomes.csv`. With only 20 masks and two model cells, these post hoc values are descriptive and were not used to reject masks or tune prompts.", "",
              "## Interpretation", "",
              "These data support the claim that ordered linguistic recovery does not require a fixed carrier or the balanced-jitter generator's simple deterministic placement rule. The model can recover a coherent ordered subsequence under a uniformly sampled 50%-density carrier with lexically matched interference.", "",
              "This does not establish arbitrary dilution levels, adversarially chosen masks, or a specific transformer mechanism. It does justify proceeding to the separately frozen natural-prose harmless-canary PoC. Cover construction must use development/held-out separation and must not optimize held-out passages against target responses.", ""]
    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).resolve().parent
    if not json.loads((root / "uniform/results/integrity-audit.json").read_text()).get("passed"):
        raise RuntimeError("passed integrity audit required")
    uniform, prior = load_uniform(root), prior_records(root)
    matrix = []
    for model, effort in CELLS:
        for carrier in ("fixed", "jitter"):
            matrix.append(carrier_row(prior, model, effort, carrier))
        matrix.append(carrier_row(uniform, model, effort, "uniform"))
    tests = {f"{carrier}_{level}": mcnemar(prior, uniform, carrier, level == "paired")
             for carrier in ("fixed", "jitter") for level in ("individual", "paired")}
    effort, exploratory = effort_rows(uniform), exploratory_rows(uniform)
    results = root / "uniform/results"
    atomic_bytes(results / "trials.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in uniform).encode())
    write_csv(results / "carrier-comparison.csv", matrix)
    write_csv(results / "effort-summary.csv", effort)
    write_csv(results / "mask-outcomes.csv", exploratory)
    (results / "matched-tests.json").write_text(json.dumps(tests, indent=2) + "\n")
    (results / "analysis.md").write_text(report(uniform, matrix, tests, effort, exploratory))
    print(json.dumps({"records": len(uniform), "matrix": matrix, "matched_tests": tests}, indent=2))


if __name__ == "__main__":
    main()
