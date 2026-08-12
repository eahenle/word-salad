#!/usr/bin/env python3
"""Behavioral, interaction, effort, and strategy analysis for Experiment 1B."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from normalize import VARIANTS

VARIANT_ORDER = ("original", "lower", "nopunct", "lower_nopunct")
CONDITION_ORDER = ("signal", "all_shuffled")
COLORS = ("#2563eb", "#7c3aed", "#059669", "#dc2626", "#d97706", "#0891b2")


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if trials == 0:
        return 0.0, 0.0
    probability = successes / trials
    denominator = 1 + z * z / trials
    center = (probability + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt(
        probability * (1 - probability) / trials + z * z / (4 * trials * trials)
    ) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def percentile(values: list[float], probability: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def median(values: list[float | int | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return statistics.median(clean) if clean else None


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summarize(records: list[dict], completed_only: bool = False) -> list[dict]:
    groups = defaultdict(list)
    for record in records:
        completed_response = record.get(
            "completed_response",
            bool(record.get("response"))
            and not bool(record.get("runner", {}).get("timed_out")),
        )
        if completed_only and not completed_response:
            continue
        groups[(record["variant"], record["condition"], int(record["lanes"]))].append(record)
    rows = []
    for variant in VARIANT_ORDER:
        for condition in CONDITION_ORDER:
            for lanes in (1, 2, 4, 8):
                group = groups.get((variant, condition, lanes), [])
                if not group:
                    continue
                trials = len(group)
                exact = sum(bool(record["exact_success"]) for record in group)
                semantic = sum(bool(record["semantic_success"]) for record in group)
                encoding = sum(bool(record["encoding_discovered"]) for record in group)
                nonresponses = sum(not bool(record.get("response")) for record in group)
                completed_responses = sum(
                    bool(
                        record.get(
                            "completed_response",
                            bool(record.get("response"))
                            and not bool(record.get("runner", {}).get("timed_out")),
                        )
                    )
                    for record in group
                )
                semantic_ci = wilson(semantic, trials)
                rows.append(
                    {
                        "variant": variant,
                        "condition": condition,
                        "lanes": lanes,
                        "trials": trials,
                        "completed_responses": completed_responses,
                        "incomplete_turns": trials - completed_responses,
                        "nonresponses": nonresponses,
                        "exact_success": exact,
                        "exact_rate": exact / trials,
                        "semantic_success": semantic,
                        "semantic_rate": semantic / trials,
                        "semantic_ci_low": semantic_ci[0],
                        "semantic_ci_high": semantic_ci[1],
                        "encoding_discovered": encoding,
                        "encoding_rate": encoding / trials,
                    }
                )
    return rows


def interactions(records: list[dict], bootstrap_samples: int = 5000) -> list[dict]:
    indexed = {
        (record["variant"], record["condition"], int(record["lanes"]), int(record["seed"])): int(
            bool(record["semantic_success"])
        )
        for record in records
    }
    rows = []
    rng = random.Random(718281828)
    for variant in VARIANT_ORDER[1:]:
        for lanes in (1, 2, 4, 8):
            seeds = [
                seed
                for seed in range(1, 11)
                if all(
                    (candidate_variant, condition, lanes, seed) in indexed
                    for candidate_variant in ("original", variant)
                    for condition in CONDITION_ORDER
                )
            ]
            if not seeds:
                continue

            def effect(sample: list[int]) -> tuple[float, float, float]:
                delta_signal = statistics.mean(
                    indexed[(variant, "signal", lanes, seed)]
                    - indexed[("original", "signal", lanes, seed)]
                    for seed in sample
                )
                delta_control = statistics.mean(
                    indexed[(variant, "all_shuffled", lanes, seed)]
                    - indexed[("original", "all_shuffled", lanes, seed)]
                    for seed in sample
                )
                return delta_signal, delta_control, delta_signal - delta_control

            delta_signal, delta_control, interaction = effect(seeds)
            boot = [
                effect([rng.choice(seeds) for _ in seeds])[2]
                for _ in range(bootstrap_samples)
            ]
            rows.append(
                {
                    "variant": variant,
                    "lanes": lanes,
                    "paired_seeds": len(seeds),
                    "delta_signal": delta_signal,
                    "delta_all_shuffled": delta_control,
                    "difference_in_differences": interaction,
                    "bootstrap_ci_low": percentile(boot, 0.025),
                    "bootstrap_ci_high": percentile(boot, 0.975),
                }
            )
    return rows


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ArithmeticError("singular regression matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column])
            ]
    return [augmented[index][-1] for index in range(size)]


def _inverse(matrix: list[list[float]]) -> list[list[float]]:
    size = len(matrix)
    columns = []
    for index in range(size):
        unit = [0.0] * size
        unit[index] = 1.0
        columns.append(_solve(matrix, unit))
    return [[columns[column][row] for column in range(size)] for row in range(size)]


def logistic_regression(records: list[dict], ridge: float = 1e-3) -> dict:
    names = [
        "intercept",
        "signal_presence",
        "lowercase",
        "punctuation_removed",
        "log2_lanes",
        "signal_x_lowercase",
        "signal_x_punctuation_removed",
        "lowercase_x_punctuation_removed",
        "signal_x_log2_lanes",
        "lowercase_x_log2_lanes",
        "punctuation_removed_x_log2_lanes",
        "signal_x_lowercase_x_punctuation_removed",
    ]
    rows = []
    outcomes = []
    for record in records:
        variant = VARIANTS[record["variant"]]
        signal_value = int(record["condition"] == "signal")
        lower = int(variant.lowercase)
        punct = int(variant.strip_punctuation)
        lane_value = math.log2(int(record["lanes"]))
        rows.append(
            [
                1.0,
                signal_value,
                lower,
                punct,
                lane_value,
                signal_value * lower,
                signal_value * punct,
                lower * punct,
                signal_value * lane_value,
                lower * lane_value,
                punct * lane_value,
                signal_value * lower * punct,
            ]
        )
        outcomes.append(float(bool(record["semantic_success"])))
    feature_count = len(names)
    beta = [0.0] * feature_count
    information = [[0.0] * feature_count for _ in range(feature_count)]
    converged = False
    for iteration in range(100):
        probabilities = []
        for row in rows:
            linear = max(-30.0, min(30.0, sum(value * coefficient for value, coefficient in zip(row, beta))))
            probabilities.append(1.0 / (1.0 + math.exp(-linear)))
        gradient = [0.0] * feature_count
        information = [[0.0] * feature_count for _ in range(feature_count)]
        for row, outcome, probability in zip(rows, outcomes, probabilities):
            weight = max(1e-9, probability * (1 - probability))
            for first in range(feature_count):
                gradient[first] += row[first] * (outcome - probability)
                for second in range(feature_count):
                    information[first][second] += weight * row[first] * row[second]
        for index in range(1, feature_count):
            gradient[index] -= ridge * beta[index]
            information[index][index] += ridge
        step = _solve(information, gradient)
        beta = [coefficient + update for coefficient, update in zip(beta, step)]
        if max(abs(update) for update in step) < 1e-8:
            converged = True
            break
    covariance = _inverse(information)
    coefficients = []
    for index, name in enumerate(names):
        standard_error = math.sqrt(max(0.0, covariance[index][index]))
        coefficients.append(
            {
                "term": name,
                "coefficient": beta[index],
                "odds_ratio": math.exp(max(-30.0, min(30.0, beta[index]))),
                "standard_error": standard_error,
                "wald_ci_low": beta[index] - 1.959963984540054 * standard_error,
                "wald_ci_high": beta[index] + 1.959963984540054 * standard_error,
            }
        )
    return {
        "outcome": "semantic_success",
        "observations": len(records),
        "ridge_penalty": ridge,
        "converged": converged,
        "iterations": iteration + 1,
        "lane_predictor": "log2(lanes)",
        "coefficients": coefficients,
        "caution": "Repeated stochastic runs of one model/runtime; coefficients describe repeatability and effect magnitude, not a population sample.",
    }


def paired_variant_contrasts(
    records: list[dict], bootstrap_samples: int = 5000
) -> list[dict]:
    """Paired seed-level normalization contrasts within condition and lane."""
    indexed = {
        (
            record["variant"],
            record["condition"],
            int(record["lanes"]),
            int(record["seed"]),
        ): int(bool(record["semantic_success"]))
        for record in records
    }
    rng = random.Random(314159265)
    rows = []
    for variant in VARIANT_ORDER[1:]:
        for condition in CONDITION_ORDER:
            for lanes in (1, 2, 4, 8):
                pairs = [
                    (
                        indexed[("original", condition, lanes, seed)],
                        indexed[(variant, condition, lanes, seed)],
                    )
                    for seed in range(1, 11)
                ]
                original_only = sum(old == 1 and new == 0 for old, new in pairs)
                normalized_only = sum(old == 0 and new == 1 for old, new in pairs)
                delta = statistics.mean(new - old for old, new in pairs)
                boots = []
                for _ in range(bootstrap_samples):
                    sample = [rng.choice(pairs) for _ in pairs]
                    boots.append(statistics.mean(new - old for old, new in sample))
                discordant = original_only + normalized_only
                # Exact two-sided McNemar/sign test on discordant pairs.
                if discordant:
                    tail = sum(
                        math.comb(discordant, value)
                        for value in range(0, min(original_only, normalized_only) + 1)
                    ) / (2**discordant)
                    exact_p = min(1.0, 2 * tail)
                else:
                    exact_p = 1.0
                rows.append(
                    {
                        "variant": variant,
                        "condition": condition,
                        "lanes": lanes,
                        "paired_seeds": len(pairs),
                        "original_success": sum(old for old, _ in pairs),
                        "normalized_success": sum(new for _, new in pairs),
                        "delta": delta,
                        "bootstrap_ci_low": percentile(boots, 0.025),
                        "bootstrap_ci_high": percentile(boots, 0.975),
                        "original_only_pairs": original_only,
                        "normalized_only_pairs": normalized_only,
                        "mcnemar_exact_p": exact_p,
                    }
                )
    return rows


def effort_summary(records: list[dict], trace_metrics: list[dict]) -> list[dict]:
    trace_by_id = {record["neutral_id"]: record for record in trace_metrics}
    groups = defaultdict(list)
    for record in records:
        trace = trace_by_id.get(record["neutral_id"], {})
        groups[(record["variant"], record["condition"], int(record["lanes"]))].append(
            (record, trace)
        )
    rows = []
    for key in sorted(groups, key=lambda value: (VARIANT_ORDER.index(value[0]), CONDITION_ORDER.index(value[1]), value[2])):
        variant, condition, lanes = key
        group = groups[key]
        rows.append(
            {
                "variant": variant,
                "condition": condition,
                "lanes": lanes,
                "trials": len(group),
                "semantic_success": sum(bool(record["semantic_success"]) for record, _ in group),
                "timeouts": sum(bool(record["runner"]["timed_out"]) for record, _ in group),
                "median_elapsed_seconds": median([record["runner"]["elapsed_seconds"] for record, _ in group]),
                "median_input_tokens": median([trace.get("input_tokens") for _, trace in group]),
                "median_cached_input_tokens": median([trace.get("cached_input_tokens") for _, trace in group]),
                "median_output_tokens": median([trace.get("output_tokens") for _, trace in group]),
                "median_reasoning_tokens": median([trace.get("reasoning_tokens") for _, trace in group]),
                "median_model_turns": median([trace.get("model_turns") for _, trace in group]),
                "median_tool_calls": median([trace.get("tool_calls") for _, trace in group]),
                "median_shell_invocations": median([trace.get("shell_invocations") for _, trace in group]),
                "median_trace_bytes": median([trace.get("trace_bytes") for _, trace in group]),
            }
        )
    return rows


def effort_rollup(records: list[dict], trace_metrics: list[dict]) -> list[dict]:
    trace_by_id = {record["neutral_id"]: record for record in trace_metrics}
    groups = defaultdict(list)
    for record in records:
        groups[(record["variant"], record["condition"])].append(
            (record, trace_by_id[record["neutral_id"]])
        )
    rows = []
    for variant in VARIANT_ORDER:
        for condition in CONDITION_ORDER:
            group = groups[(variant, condition)]
            rows.append(
                {
                    "variant": variant,
                    "condition": condition,
                    "trials": len(group),
                    "semantic_success": sum(bool(record["semantic_success"]) for record, _ in group),
                    "completed_responses": sum(bool(record["completed_response"]) for record, _ in group),
                    "timeouts": sum(bool(record["runner"]["timed_out"]) for record, _ in group),
                    "trials_with_tools": sum(trace["tool_calls"] > 0 for _, trace in group),
                    "trials_with_shell": sum(trace["shell_invocations"] > 0 for _, trace in group),
                    "median_elapsed_seconds": median([record["runner"]["elapsed_seconds"] for record, _ in group]),
                    "median_input_tokens": median([trace.get("input_tokens") for _, trace in group]),
                    "median_cached_input_tokens": median([trace.get("cached_input_tokens") for _, trace in group]),
                    "median_output_tokens": median([trace.get("output_tokens") for _, trace in group]),
                    "median_reasoning_tokens": median([trace.get("reasoning_tokens") for _, trace in group]),
                    "median_trace_bytes": median([trace.get("trace_bytes") for _, trace in group]),
                }
            )
    return rows


def strategy_summary(trace_metrics: list[dict]) -> list[dict]:
    groups = defaultdict(Counter)
    for record in trace_metrics:
        groups[(record["variant"], record["condition"])][record["strategy"]] += 1
    rows = []
    for (variant, condition), counts in sorted(
        groups.items(), key=lambda item: (VARIANT_ORDER.index(item[0][0]), CONDITION_ORDER.index(item[0][1]))
    ):
        for strategy, count in sorted(counts.items()):
            rows.append(
                {
                    "variant": variant,
                    "condition": condition,
                    "strategy": strategy,
                    "trials": count,
                }
            )
    return rows


def strategy_outcome_summary(records: list[dict], trace_metrics: list[dict]) -> list[dict]:
    success_by_id = {
        record["neutral_id"]: bool(record["semantic_success"]) for record in records
    }
    groups = defaultdict(Counter)
    for trace in trace_metrics:
        groups[(trace["condition"], success_by_id[trace["neutral_id"]])][
            trace["strategy"]
        ] += 1
    rows = []
    for condition in CONDITION_ORDER:
        for success in (True, False):
            for strategy, count in sorted(groups[(condition, success)].items()):
                rows.append(
                    {
                        "condition": condition,
                        "semantic_success": success,
                        "strategy": strategy,
                        "trials": count,
                    }
                )
    return rows


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_chart(
    path: Path,
    *,
    title: str,
    x_labels: list[str],
    series: list[dict],
    y_label: str = "rate",
    y_min: float = 0.0,
    y_max: float = 1.0,
) -> None:
    width, height = 900, 520
    left, right, top, bottom = 90, 30, 60, 100
    plot_width, plot_height = width - left - right, height - top - bottom
    x_positions = [
        left + index * plot_width / max(1, len(x_labels) - 1)
        for index in range(len(x_labels))
    ]

    def y(value: float) -> float:
        clipped = max(y_min, min(y_max, value))
        return top + (y_max - clipped) / (y_max - y_min) * plot_height

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="30" text-anchor="middle" font-family="sans-serif" font-size="20" font-weight="600">{_escape(title)}</text>',
    ]
    for tick in range(6):
        value = y_min + (y_max - y_min) * tick / 5
        position = y(value)
        elements.append(f'<line x1="{left}" y1="{position:.1f}" x2="{width-right}" y2="{position:.1f}" stroke="#e5e7eb"/>')
        elements.append(f'<text x="{left-12}" y="{position+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="12">{value:.1f}</text>')
    elements.append(f'<text x="22" y="{top+plot_height/2}" transform="rotate(-90 22 {top+plot_height/2})" text-anchor="middle" font-family="sans-serif" font-size="13">{_escape(y_label)}</text>')
    for index, label in enumerate(x_labels):
        elements.append(f'<text x="{x_positions[index]:.1f}" y="{height-bottom+26}" text-anchor="middle" font-family="sans-serif" font-size="12">{_escape(label)}</text>')
    for series_index, item in enumerate(series):
        color = item.get("color", COLORS[series_index % len(COLORS)])
        points = []
        for index, value in enumerate(item["values"]):
            if value is None:
                continue
            if isinstance(value, (tuple, list)):
                estimate, low, high = value
            else:
                estimate, low, high = value, None, None
            x_position = x_positions[index]
            points.append(f"{x_position:.1f},{y(estimate):.1f}")
            if low is not None and high is not None:
                elements.append(f'<line x1="{x_position:.1f}" y1="{y(high):.1f}" x2="{x_position:.1f}" y2="{y(low):.1f}" stroke="{color}"/>')
            elements.append(f'<circle cx="{x_position:.1f}" cy="{y(estimate):.1f}" r="5" fill="{color}"/>')
        if points:
            elements.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        legend_x = left + (series_index % 4) * 195
        legend_y = height - 52 + (series_index // 4) * 18
        elements.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x+24}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        elements.append(f'<text x="{legend_x+30}" y="{legend_y+4}" font-family="sans-serif" font-size="11">{_escape(item["name"])}</text>')
    elements.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(elements) + "\n", encoding="utf-8")


def make_figures(summary_rows: list[dict], interaction_rows: list[dict], figures: Path) -> None:
    lookup = {
        (row["variant"], row["condition"], row["lanes"]): (
            row["semantic_rate"], row["semantic_ci_low"], row["semantic_ci_high"]
        )
        for row in summary_rows
    }
    lane_labels = ["1", "2", "4", "8"]
    for condition in CONDITION_ORDER:
        write_chart(
            figures / f"semantic-success-vs-n-{condition}.svg",
            title=f"Semantic success vs. N — {condition}",
            x_labels=lane_labels,
            series=[
                {
                    "name": variant,
                    "values": [lookup.get((variant, condition, lane)) for lane in (1, 2, 4, 8)],
                }
                for variant in VARIANT_ORDER
            ],
        )
    for variant in VARIANT_ORDER:
        write_chart(
            figures / f"signal-vs-all-shuffled-{variant}.svg",
            title=f"Signal vs. all shuffled — {variant}",
            x_labels=lane_labels,
            series=[
                {
                    "name": condition,
                    "values": [lookup.get((variant, condition, lane)) for lane in (1, 2, 4, 8)],
                }
                for condition in CONDITION_ORDER
            ],
        )
    for condition in CONDITION_ORDER:
        series = []
        for lane in (1, 2, 4, 8):
            baseline = lookup.get(("original", condition, lane))
            values = []
            for variant in VARIANT_ORDER[1:]:
                current = lookup.get((variant, condition, lane))
                values.append(None if baseline is None or current is None else current[0] - baseline[0])
            series.append({"name": f"N={lane}", "values": values})
        write_chart(
            figures / f"normalization-effect-{condition}.svg",
            title=f"Change from original — {condition}",
            x_labels=list(VARIANT_ORDER[1:]),
            series=series,
            y_label="rate change",
            y_min=-1.0,
            y_max=1.0,
        )
    interaction_lookup = {
        (row["variant"], row["lanes"]): (
            row["difference_in_differences"], row["bootstrap_ci_low"], row["bootstrap_ci_high"]
        )
        for row in interaction_rows
    }
    write_chart(
        figures / "normalization-interaction.svg",
        title="Normalization × signal-presence interaction",
        x_labels=list(VARIANT_ORDER[1:]),
        series=[
            {
                "name": f"N={lane}",
                "values": [interaction_lookup.get((variant, lane)) for variant in VARIANT_ORDER[1:]],
            }
            for lane in (1, 2, 4, 8)
        ],
        y_label="difference in differences",
        y_min=-1.0,
        y_max=1.0,
    )


def historical_counts(path: Path) -> dict[tuple[str, int], tuple[int, int]]:
    counts = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            counts[(row["condition"], int(row["lanes"]))] = (
                int(row["semantic_success"]), int(row["trials"])
            )
    return counts


def write_report(
    path: Path,
    *,
    dataset_label: str,
    invalidated: bool,
    records: list[dict],
    summary_rows: list[dict],
    completed_rows: list[dict],
    interaction_rows: list[dict],
    effort_rows: list[dict],
    effort_rollup_rows: list[dict],
    strategy_rows: list[dict],
    strategy_outcome_rows: list[dict],
    paired_contrast_rows: list[dict],
    trace_metrics: list[dict],
    historical: dict,
) -> None:
    lookup = {(row["variant"], row["condition"], row["lanes"]): row for row in summary_rows}
    lines = [
        f"# {dataset_label} analysis",
        "",
        "Rates use all scheduled trials unless explicitly labeled completed-response-only. Intervals are 95% Wilson score intervals. Interaction intervals use a deterministic paired-seed bootstrap.",
        "",
        "## Replication versus frozen historical baseline",
        "",
        "| condition | lanes | historical semantic | replication semantic |",
        "| :-- | --: | --: | --: |",
    ]
    if invalidated:
        lines[2:2] = [
            "> **INVALIDATED DATASET — FORENSIC USE ONLY.** Post-slate trace review found behavior-dependent host filesystem leakage. See `invalidation-report.md` and `leakage-trace-audit-summary.json`. These results must not be used for confirmatory inference or pooled with a hardened rerun.",
            "",
        ]
    for condition in CONDITION_ORDER:
        for lane in (1, 2, 4, 8):
            old = historical.get((condition, lane))
            new = lookup.get(("original", condition, lane))
            lines.append(
                f"| {condition} | {lane} | "
                f"{old[0]}/{old[1] if old else '?'}" if old else f"| {condition} | {lane} | unavailable"
            )
            if old:
                lines[-1] += f" | {new['semantic_success']}/{new['trials']} |" if new else " | pending |"
            else:
                lines[-1] += " | pending |"
    lines.extend(
        [
            "",
            "## Complete scheduled-denominator matrix",
            "",
            "| variant | condition | N | trials | semantic | rate | 95% CI | nonresponses |",
            "| :-- | :-- | --: | --: | --: | --: | :-- | --: |",
        ]
    )
    for row in summary_rows:
        lines.append(
            f"| {row['variant']} | {row['condition']} | {row['lanes']} | {row['trials']} | "
            f"{row['semantic_success']} | {row['semantic_rate']:.0%} | "
            f"{row['semantic_ci_low']:.0%}–{row['semantic_ci_high']:.0%} | {row['nonresponses']} |"
        )
    completed_lookup = {
        (row["variant"], row["condition"], row["lanes"]): row
        for row in completed_rows
    }
    affected = [
        row for row in summary_rows if row["completed_responses"] < row["trials"]
    ]
    lines.extend(
        [
            "",
            "## Completed-response sensitivity",
            "",
            "Only cells containing an incomplete turn are shown. The scheduled denominator remains primary.",
            "",
            "| variant | condition | N | scheduled semantic | completed-response semantic |",
            "| :-- | :-- | --: | --: | --: |",
        ]
    )
    for row in affected:
        completed = completed_lookup[(row["variant"], row["condition"], row["lanes"])]
        lines.append(
            f"| {row['variant']} | {row['condition']} | {row['lanes']} | "
            f"{row['semantic_success']}/{row['trials']} | "
            f"{completed['semantic_success']}/{completed['trials']} |"
        )
    lines.extend(
        [
            "",
            "## Normalization interaction",
            "",
            "Positive difference-in-differences means normalization reduced all-shuffled success more than signal success.",
            "",
            "| variant | N | Δ signal | Δ all shuffled | interaction | bootstrap 95% CI |",
            "| :-- | --: | --: | --: | --: | :-- |",
        ]
    )
    for row in interaction_rows:
        lines.append(
            f"| {row['variant']} | {row['lanes']} | {row['delta_signal']:+.0%} | "
            f"{row['delta_all_shuffled']:+.0%} | {row['difference_in_differences']:+.0%} | "
            f"{row['bootstrap_ci_low']:+.0%}–{row['bootstrap_ci_high']:+.0%} |"
        )
    lines.extend(
        [
            "",
            "## Paired seed-level normalization contrasts",
            "",
            "Each row compares the same latent prompt geometry and seed against original. The exact p-value is a two-sided McNemar/sign test over discordant pairs; it is descriptive, not population inference.",
            "",
            "| variant | condition | N | original | normalized | delta | bootstrap 95% CI | discordant old/new | exact p |",
            "| :-- | :-- | --: | --: | --: | --: | :-- | :-- | --: |",
        ]
    )
    for row in paired_contrast_rows:
        lines.append(
            f"| {row['variant']} | {row['condition']} | {row['lanes']} | "
            f"{row['original_success']}/10 | {row['normalized_success']}/10 | "
            f"{row['delta']:+.0%} | {row['bootstrap_ci_low']:+.0%}–{row['bootstrap_ci_high']:+.0%} | "
            f"{row['original_only_pairs']}/{row['normalized_only_pairs']} | "
            f"{row['mcnemar_exact_p']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Computational effort",
            "",
            "Medians exclude missing usage from incomplete turns. Timeouts remain in timeout counts and elapsed-time medians. Full N-level metrics are in `effort-summary.csv`.",
            "",
            "| variant | condition | semantic | timeouts | tool trials | shell trials | median elapsed (s) | median input tokens | median reasoning tokens |",
            "| :-- | :-- | --: | --: | --: | --: | --: | --: | --: |",
        ]
    )
    for row in effort_rollup_rows:
        lines.append(
            f"| {row['variant']} | {row['condition']} | {row['semantic_success']}/{row['trials']} | "
            f"{row['timeouts']} | {row['trials_with_tools']} | {row['trials_with_shell']} | "
            f"{row['median_elapsed_seconds']:.1f} | {row['median_input_tokens']:.0f} | "
            f"{row['median_reasoning_tokens']:.0f} |"
        )
    signal_timeouts = sum(
        row["timeouts"] for row in effort_rollup_rows if row["condition"] == "signal"
    )
    shuffled_timeouts = sum(
        row["timeouts"]
        for row in effort_rollup_rows
        if row["condition"] == "all_shuffled"
    )
    signal_tool_trials = sum(
        row["trials_with_tools"]
        for row in effort_rollup_rows
        if row["condition"] == "signal"
    )
    shuffled_tool_trials = sum(
        row["trials_with_tools"]
        for row in effort_rollup_rows
        if row["condition"] == "all_shuffled"
    )
    max_context = max(
        (row for row in effort_rows if row["median_input_tokens"] is not None),
        key=lambda row: row["median_input_tokens"],
    )
    lines.extend(
        [
            "",
            f"Across variants, all-shuffled trials produced {shuffled_timeouts}/160 timeouts and tool use in {shuffled_tool_trials}/160 trials, versus {signal_timeouts}/160 timeouts and tool use in {signal_tool_trials}/160 signal trials.",
            f"The largest cell median input context was {max_context['median_input_tokens']:.0f} tokens for {max_context['variant']} / {max_context['condition']} / N={max_context['lanes']}.",
            "",
            "## Trace-derived strategies",
            "",
            "Strategy labels describe only observable JSONL events. They do not expose private chain-of-thought.",
            "",
            "| condition | semantic success | observable primary strategy | trials |",
            "| :-- | :-- | :-- | --: |",
        ]
    )
    for row in strategy_outcome_rows:
        lines.append(
            f"| {row['condition']} | {'yes' if row['semantic_success'] else 'no'} | "
            f"{row['strategy']} | {row['trials']} |"
        )
    lines.extend(
        [
            "",
            "The finer variant-by-condition strategy table is in `strategy-summary.csv`.",
            "",
            "| variant | condition | strategy | trials |",
            "| :-- | :-- | :-- | --: |",
        ]
    )
    for row in strategy_rows:
        lines.append(
            f"| {row['variant']} | {row['condition']} | {row['strategy']} | {row['trials']} |"
        )
    substitutions = sum(bool(record["malformed_object_substitutions"]) for record in records)
    encoding = sum(bool(record["encoding_discovered"]) for record in records)
    timeouts = sum(bool(record["runner"]["timed_out"]) for record in records)
    trace_by_id = {trace["neutral_id"]: trace for trace in trace_metrics}
    correct_signal = [
        record
        for record in records
        if record["condition"] == "signal" and record["semantic_success"]
    ]
    correct_control = [
        record
        for record in records
        if record["condition"] == "all_shuffled" and record["semantic_success"]
    ]
    correct_signal_direct = sum(
        trace_by_id[record["neutral_id"]]["strategy"] == "direct_one_pass_response"
        for record in correct_signal
    )
    correct_signal_tools = sum(
        trace_by_id[record["neutral_id"]]["tool_calls"] > 0 for record in correct_signal
    )
    correct_control_tools = sum(
        trace_by_id[record["neutral_id"]]["tool_calls"] > 0 for record in correct_control
    )
    lines.extend(
        [
            "",
            "## Observable unusual behavior counts",
            "",
            f"- Timeout/nonresponse runner events: {timeouts}",
            f"- Final responses explicitly mentioning shuffle/encoding: {encoding}",
            f"- Responses with malformed object substitutions: {substitutions}",
            f"- Correct signal trials with a direct/no-tool/no-explicit-reconstruction primary trace label: {correct_signal_direct}/{len(correct_signal)}",
            f"- Correct signal trials with any observable tool call: {correct_signal_tools}/{len(correct_signal)}",
            f"- Correct all-shuffled trials with any observable tool call: {correct_control_tools}/{len(correct_control)}",
            "- Some timed-out traces ended on progress messages after recognizing the task or scrambling; those are not final task successes.",
            "- Several failures substituted material/object pairs such as `brass coin` or `silver key`, consistent with lexical recombination rather than reliable relational recovery.",
            "",
            "## Conclusion and next step",
            "",
            "The preregistered directional hypothesis was not supported. Normalization did eliminate or reduce the original N=8 all-shuffled successes, but it generally damaged intact-signal recovery as much or more; the paired interaction estimates were zero or negative in most cells. The result therefore does not isolate punctuation/capitalization as a cue used disproportionately for unordered reconstruction.",
            "",
            "The fully instrumented replication did reproduce robust blind task recovery and substantial run-to-run variability. Observable traces separate many cheap direct responses from expensive tool-assisted reconstruction, but a direct final response cannot establish implicit decoding because the payload itself suppresses explanation.",
            "",
            "Proceed to the preregistered equal-multiset A/B Experiment 2 without changing its central design. Its answer-identity endpoint is more discriminating than another success-rate comparison. Retain full traces, the explanation-permitted arm, and the tool-less regime so that ordered-channel sensitivity can be separated from explicit agentic reconstruction.",
            "",
            "## Interpretation boundary",
            "",
            "Correct all-shuffled answers are not periodic-lane recovery. Final-answer silence about encoding is not evidence that encoding was not consciously discovered, especially because the payload suppresses explanation. Statistical summaries describe repeatability for this model/runtime rather than classical population inference.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--trials", type=Path, default=root / "results" / "trials.jsonl")
    parser.add_argument("--trace-metrics", type=Path, default=root / "results" / "trace-metrics.jsonl")
    parser.add_argument("--historical-summary", type=Path, default=root.parent / "multiplex-experiment" / "results" / "summary.csv")
    parser.add_argument(
        "--dataset-label",
        help="report title; defaults to the experiment directory name",
    )
    parser.add_argument(
        "--invalidated",
        action="store_true",
        help="emit the forensic-only invalidation warning",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    records = [json.loads(line) for line in args.trials.read_text(encoding="utf-8").splitlines() if line.strip()]
    traces = [json.loads(line) for line in args.trace_metrics.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = args.root / "results"
    scheduled = summarize(records, completed_only=False)
    completed = summarize(records, completed_only=True)
    interaction_rows = interactions(records)
    paired_contrast_rows = paired_variant_contrasts(records)
    effort_rows = effort_summary(records, traces)
    effort_rollup_rows = effort_rollup(records, traces)
    strategy_rows = strategy_summary(traces)
    strategy_outcome_rows = strategy_outcome_summary(records, traces)
    regression = logistic_regression(records)
    write_csv(results / "summary.csv", scheduled)
    write_csv(results / "summary-completed-responses.csv", completed)
    write_csv(results / "interaction.csv", interaction_rows)
    write_csv(results / "paired-contrasts.csv", paired_contrast_rows)
    write_csv(results / "effort-summary.csv", effort_rows)
    write_csv(results / "effort-rollup.csv", effort_rollup_rows)
    write_csv(results / "strategy-summary.csv", strategy_rows)
    write_csv(results / "strategy-outcome-summary.csv", strategy_outcome_rows)
    (results / "logistic-regression.json").write_text(json.dumps(regression, indent=2) + "\n", encoding="utf-8")
    make_figures(scheduled, interaction_rows, results / "figures")
    write_report(
        results / "analysis.md",
        dataset_label=args.dataset_label or args.root.name,
        invalidated=args.invalidated,
        records=records,
        summary_rows=scheduled,
        completed_rows=completed,
        interaction_rows=interaction_rows,
        effort_rows=effort_rows,
        effort_rollup_rows=effort_rollup_rows,
        strategy_rows=strategy_rows,
        strategy_outcome_rows=strategy_outcome_rows,
        paired_contrast_rows=paired_contrast_rows,
        trace_metrics=traces,
        historical=historical_counts(args.historical_summary),
    )
    print(f"analyzed {len(records)} scored trials and {len(traces)} traces")


if __name__ == "__main__":
    main()
