#!/usr/bin/env python3
"""Aggregate scored JSONL, compute Wilson intervals, and render dependency-free SVGs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if trials == 0:
        return 0.0, 0.0
    probability = successes / trials
    denominator = 1 + z * z / trials
    center = (probability + z * z / (2 * trials)) / denominator
    margin = (
        z
        * math.sqrt(probability * (1 - probability) / trials + z * z / (4 * trials * trials))
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def summarize(records: list[dict]) -> list[dict]:
    groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for record in records:
        groups[(record["condition"], int(record["lanes"]))].append(record)
    rows = []
    for (condition, lanes), group in sorted(groups.items()):
        trials = len(group)
        exact = sum(bool(record["exact_success"]) for record in group)
        semantic = sum(bool(record["semantic_success"]) for record in group)
        encoding = sum(bool(record["encoding_discovered"]) for record in group)
        nonresponses = sum(not record.get("response") for record in group)
        exact_ci = wilson(exact, trials)
        semantic_ci = wilson(semantic, trials)
        encoding_ci = wilson(encoding, trials)
        rows.append(
            {
                "condition": condition,
                "lanes": lanes,
                "trials": trials,
                "completed_responses": trials - nonresponses,
                "nonresponses": nonresponses,
                "exact_success": exact,
                "exact_rate": exact / trials,
                "exact_ci_low": exact_ci[0],
                "exact_ci_high": exact_ci[1],
                "semantic_success": semantic,
                "semantic_rate": semantic / trials,
                "semantic_ci_low": semantic_ci[0],
                "semantic_ci_high": semantic_ci[1],
                "encoding_discovered": encoding,
                "encoding_rate": encoding / trials,
                "encoding_ci_low": encoding_ci[0],
                "encoding_ci_high": encoding_ci[1],
            }
        )
    return rows


def write_summary_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def write_svg_chart(
    *,
    path: Path,
    title: str,
    y_label: str,
    lanes: list[int | float],
    series: list[dict],
    x_label: str = "lanes",
) -> None:
    width, height = 820, 500
    left, right, top, bottom = 80, 30, 60, 70
    plot_width = width - left - right
    plot_height = height - top - bottom
    x_positions = {
        lane: left + (index * plot_width / max(1, len(lanes) - 1))
        for index, lane in enumerate(lanes)
    }

    def y_position(value: float) -> float:
        return top + (1 - value) * plot_height

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-family="sans-serif" font-size="20" font-weight="600">{_escape(title)}</text>',
    ]
    for tick in range(0, 6):
        value = tick / 5
        y = y_position(value)
        elements.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e5e7eb"/>',
                f'<text x="{left-12}" y="{y+5:.1f}" text-anchor="end" font-family="sans-serif" font-size="12">{value:.1f}</text>',
            ]
        )
    elements.extend(
        [
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#111827"/>',
            f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#111827"/>',
            f'<text x="20" y="{top + plot_height/2}" transform="rotate(-90 20 {top + plot_height/2})" text-anchor="middle" font-family="sans-serif" font-size="13">{_escape(y_label)}</text>',
            f'<text x="{left + plot_width/2}" y="{height-20}" text-anchor="middle" font-family="sans-serif" font-size="13">{_escape(x_label)}</text>',
        ]
    )
    for lane in lanes:
        x = x_positions[lane]
        elements.append(
            f'<text x="{x:.1f}" y="{height-bottom+24}" text-anchor="middle" font-family="sans-serif" font-size="12">{lane}</text>'
        )
    for series_index, item in enumerate(series):
        color = item["color"]
        points = []
        for lane in lanes:
            if lane not in item["values"]:
                continue
            value, low, high = item["values"][lane]
            x = x_positions[lane]
            y = y_position(value)
            points.append(f"{x:.1f},{y:.1f}")
            elements.extend(
                [
                    f'<line x1="{x:.1f}" y1="{y_position(high):.1f}" x2="{x:.1f}" y2="{y_position(low):.1f}" stroke="{color}"/>',
                    f'<line x1="{x-5:.1f}" y1="{y_position(high):.1f}" x2="{x+5:.1f}" y2="{y_position(high):.1f}" stroke="{color}"/>',
                    f'<line x1="{x-5:.1f}" y1="{y_position(low):.1f}" x2="{x+5:.1f}" y2="{y_position(low):.1f}" stroke="{color}"/>',
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}"/>',
                ]
            )
        if points:
            elements.append(
                f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.5"/>'
            )
        legend_x = left + series_index * 210
        elements.extend(
            [
                f'<line x1="{legend_x}" y1="{height-48}" x2="{legend_x+28}" y2="{height-48}" stroke="{color}" stroke-width="3"/>',
                f'<text x="{legend_x+36}" y="{height-43}" font-family="sans-serif" font-size="12">{_escape(item["name"])}</text>',
            ]
        )
    elements.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(elements) + "\n", encoding="utf-8")


def values_for(rows: list[dict], condition: str, metric: str) -> dict[int, tuple[float, float, float]]:
    return {
        row["lanes"]: (
            row[f"{metric}_rate"],
            row[f"{metric}_ci_low"],
            row[f"{metric}_ci_high"],
        )
        for row in rows
        if row["condition"] == condition
    }


def write_analysis_markdown(records: list[dict], rows: list[dict], path: Path) -> None:
    categories: dict[str, int] = defaultdict(int)
    for record in records:
        categories[record["classification"]] += 1
    signal_rows = [row for row in rows if row["condition"] == "signal"]
    control_rows = [row for row in rows if row["condition"] == "all_shuffled"]
    lines = [
        "# Experiment analysis",
        "",
        "Rates use all scheduled trials as the denominator, including capped nonresponses. Intervals are 95% Wilson score intervals.",
        "",
        "## Signal trials",
        "",
        "| lanes | trials | exact success | semantic success | encoding discovered | nonresponses |",
        "| ----: | -----: | ------------: | ---------------: | ------------------: | -----------: |",
    ]
    for row in signal_rows:
        lines.append(
            f"| {row['lanes']} | {row['trials']} | {row['exact_success']} | {row['semantic_success']} | {row['encoding_discovered']} | {row['nonresponses']} |"
        )
    lines.extend(
        [
            "",
            "## All-shuffled controls",
            "",
            "| lanes | trials | exact success | semantic success | encoding discovered | nonresponses |",
            "| ----: | -----: | ------------: | ---------------: | ------------------: | -----------: |",
        ]
    )
    for row in control_rows:
        lines.append(
            f"| {row['lanes']} | {row['trials']} | {row['exact_success']} | {row['semantic_success']} | {row['encoding_discovered']} | {row['nonresponses']} |"
        )
    lines.extend(["", "## Classification totals", ""])
    for category, count in sorted(categories.items()):
        lines.append(f"- `{category}`: {count}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=here / "results" / "trials.jsonl")
    parser.add_argument("--summary", type=Path, default=here / "results" / "summary.csv")
    parser.add_argument("--figures", type=Path, default=here / "results" / "figures")
    parser.add_argument("--report", type=Path, default=here / "results" / "analysis.md")
    return parser


def main() -> None:
    args = _parser().parse_args()
    records = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not records:
        raise ValueError("no trial records")
    rows = summarize(records)
    write_summary_csv(rows, args.summary)
    write_analysis_markdown(records, rows, args.report)
    lanes = sorted({row["lanes"] for row in rows})
    write_svg_chart(
        path=args.figures / "semantic-success-vs-lanes.svg",
        title="Semantic task success vs. lane count",
        y_label="success rate",
        lanes=lanes,
        series=[
            {
                "name": "signal",
                "color": "#2563eb",
                "values": values_for(rows, "signal", "semantic"),
            }
        ],
    )
    write_svg_chart(
        path=args.figures / "encoding-discovery-vs-lanes.svg",
        title="Explicit encoding discovery vs. lane count",
        y_label="discovery rate",
        lanes=lanes,
        series=[
            {
                "name": "signal",
                "color": "#7c3aed",
                "values": values_for(rows, "signal", "encoding"),
            },
            {
                "name": "all shuffled",
                "color": "#d97706",
                "values": values_for(rows, "all_shuffled", "encoding"),
            },
        ],
    )
    write_svg_chart(
        path=args.figures / "signal-vs-all-shuffled.svg",
        title="Signal vs. all-shuffled semantic success",
        y_label="success rate",
        lanes=lanes,
        series=[
            {
                "name": "signal",
                "color": "#2563eb",
                "values": values_for(rows, "signal", "semantic"),
            },
            {
                "name": "all shuffled",
                "color": "#dc2626",
                "values": values_for(rows, "all_shuffled", "semantic"),
            },
        ],
    )
    corruption = [record for record in records if record["condition"] == "corrupt_signal"]
    if corruption:
        groups: dict[float, list[dict]] = defaultdict(list)
        for record in corruption:
            groups[float(record["corruption_fraction"])].append(record)
        fractions = sorted(groups)
        corruption_values = {}
        for fraction, group in sorted(groups.items()):
            successes = sum(record["semantic_success"] for record in group)
            low, high = wilson(successes, len(group))
            corruption_values[fraction] = (successes / len(group), low, high)
        write_svg_chart(
            path=args.figures / "corruption-success.svg",
            title="Success vs. signal corruption",
            y_label="success rate",
            lanes=fractions,
            series=[{"name": "corrupt signal", "color": "#059669", "values": corruption_values}],
            x_label="corruption fraction",
        )
    print(f"analyzed {len(records)} trials")


if __name__ == "__main__":
    main()
