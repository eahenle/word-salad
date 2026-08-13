#!/usr/bin/env python3
"""Analyze the frozen cost-truncated tool-less pilot and matched Codex trials."""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


COLORS = ("#2563eb", "#dc2626", "#059669", "#7c3aed")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if not trials:
        return 0.0, 0.0
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def median(values: list[float | int | None]) -> float | None:
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


def cell_rows(records: list[dict], regime: str) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        groups[(record["condition"], record["lanes"], record.get("payload_identity") or "none")].append(record)
    output = []
    for key in sorted(groups):
        group = groups[key]
        successes = sum(bool(record["semantic_success"]) for record in group)
        low, high = wilson(successes, len(group))
        completed = [record for record in group if record["completed_response"]]
        target_answers = sum(record["observed_answer_identity"] in {"A", "B"} for record in group)
        output.append({
            "regime": regime,
            "condition": key[0],
            "lanes": key[1],
            "stimulus_identity": key[2],
            "scheduled": len(group),
            "completed_responses": len(completed),
            "timeout_nonresponses": sum(bool(record["runner"]["timed_out"]) for record in group),
            "answer_A": sum(record["observed_answer_identity"] == "A" for record in group),
            "answer_B": sum(record["observed_answer_identity"] == "B" for record in group),
            "target_answers": target_answers,
            "other_or_no_answer": len(group) - target_answers,
            "exact_success": sum(bool(record["exact_success"]) for record in group),
            "semantic_success": successes,
            "scheduled_success_rate": successes / len(group),
            "success_ci_low": low,
            "success_ci_high": high,
            "completed_success_rate": (
                sum(bool(record["semantic_success"]) for record in completed) / len(completed)
                if completed else None
            ),
            "encoding_discovered_in_final": sum(
                bool(record["encoding_discovered_in_final"]) for record in group
            ),
        })
    return output


def paired_row(records: list[dict], regime: str) -> dict:
    signal = {
        (record["seed"], record["payload_identity"]): record
        for record in records if record["condition"] == "signal" and record["lanes"] == 2
    }
    pairs = [(signal[(seed, "A")], signal[(seed, "B")]) for seed in range(1, 21)]
    both = sum(a["semantic_success"] and b["semantic_success"] for a, b in pairs)
    low, high = wilson(both, len(pairs))
    return {
        "regime": regime,
        "pairs": len(pairs),
        "A_to_A_and_B_to_B": both,
        "paired_discrimination_rate": both / len(pairs),
        "ci_low": low,
        "ci_high": high,
        "A_expected_B_not": sum(a["semantic_success"] and not b["semantic_success"] for a, b in pairs),
        "B_expected_A_not": sum(b["semantic_success"] and not a["semantic_success"] for a, b in pairs),
        "neither_expected": sum(not a["semantic_success"] and not b["semantic_success"] for a, b in pairs),
        "same_A_answer": sum(a["observed_answer_identity"] == b["observed_answer_identity"] == "A" for a, b in pairs),
        "same_B_answer": sum(a["observed_answer_identity"] == b["observed_answer_identity"] == "B" for a, b in pairs),
    }


def raw_reasoning_items(root: Path, trial_id: str) -> int | None:
    outcome_path = root / "raw-model" / "outcomes" / f"{trial_id}.json"
    if not outcome_path.exists():
        return None
    outcome = json.loads(outcome_path.read_text())
    response = json.loads((root / outcome["response_file"]).read_text())
    return sum(
        isinstance(item, dict) and item.get("type") == "reasoning"
        for item in response.get("output") or []
    )


def effort_rows(
    root: Path,
    tool: list[dict],
    codex: list[dict],
    codex_metrics: dict[str, dict],
) -> list[dict]:
    output = []
    for regime, records in (("tool_less", tool), ("codex_agent", codex)):
        for condition in ("clean", "signal", "all_shuffled"):
            group = [record for record in records if record["condition"] == condition]
            usages = [record["runner"].get("aggregate_usage") or {} for record in group]
            if regime == "tool_less":
                reasoning = [
                    (usage.get("output_tokens_details") or {}).get("reasoning_tokens")
                    for usage in usages
                ]
                reasoning_items = [raw_reasoning_items(root, record["neutral_id"]) for record in group]
                tool_users = 0
                tool_calls = [0 for _ in group]
                model_turns = [1 if record["completed_response"] else None for record in group]
                trace_bytes = [
                    record["runner"].get("response_bytes") if record["completed_response"] else None
                    for record in group
                ]
            else:
                reasoning = [usage.get("reasoning_output_tokens") for usage in usages]
                metrics = [codex_metrics[record["neutral_id"]] for record in group]
                reasoning_items = [metric["reasoning_items"] for metric in metrics]
                tool_users = sum(metric["tool_calls"] > 0 for metric in metrics)
                tool_calls = [metric["tool_calls"] for metric in metrics]
                model_turns = [metric["model_turns"] for metric in metrics]
                trace_bytes = [metric["trace_bytes"] for metric in metrics]
            output.append({
                "regime": regime,
                "condition": condition,
                "lanes": 1 if condition == "clean" else 2,
                "scheduled": len(group),
                "completed_responses": sum(record["completed_response"] for record in group),
                "timeouts": sum(record["runner"]["timed_out"] for record in group),
                "tool_using_trials": tool_users,
                "median_elapsed_seconds_scheduled": median([
                    record["runner"].get("elapsed_seconds") for record in group
                ]),
                "median_input_tokens_returned": median([usage.get("input_tokens") for usage in usages]),
                "median_output_tokens_returned": median([usage.get("output_tokens") for usage in usages]),
                "median_reasoning_tokens_returned": median(reasoning),
                "median_emitted_reasoning_items_returned": median(reasoning_items),
                "median_model_turns": median(model_turns),
                "median_tool_calls": median(tool_calls),
                "median_trace_or_response_bytes_returned": median(trace_bytes),
            })
    return output


def discordance_rows(tool: list[dict], codex: list[dict]) -> list[dict]:
    tool_by_id = {record["neutral_id"]: record for record in tool}
    codex_by_id = {record["neutral_id"]: record for record in codex}
    output = []
    for condition in ("clean", "signal", "all_shuffled"):
        ids = [trial_id for trial_id, record in tool_by_id.items() if record["condition"] == condition]
        if condition == "all_shuffled":
            outcome = lambda record: record["observed_answer_identity"] in {"A", "B"}
            endpoint = "produced_A_or_B_target_answer"
        else:
            outcome = lambda record: bool(record["semantic_success"])
            endpoint = "expected_answer_success"
        both = sum(outcome(tool_by_id[i]) and outcome(codex_by_id[i]) for i in ids)
        tool_only = sum(outcome(tool_by_id[i]) and not outcome(codex_by_id[i]) for i in ids)
        codex_only = sum(outcome(codex_by_id[i]) and not outcome(tool_by_id[i]) for i in ids)
        neither = sum(not outcome(tool_by_id[i]) and not outcome(codex_by_id[i]) for i in ids)
        output.append({
            "condition": condition,
            "endpoint": endpoint,
            "matched_trials": len(ids),
            "both": both,
            "tool_less_only": tool_only,
            "codex_agent_only": codex_only,
            "neither": neither,
        })
    tool_signal = {(record["seed"], record["payload_identity"]): record for record in tool if record["condition"] == "signal"}
    codex_signal = {(record["seed"], record["payload_identity"]): record for record in codex if record["condition"] == "signal"}
    tool_pair = {
        seed: tool_signal[(seed, "A")]["semantic_success"] and tool_signal[(seed, "B")]["semantic_success"]
        for seed in range(1, 21)
    }
    codex_pair = {
        seed: codex_signal[(seed, "A")]["semantic_success"] and codex_signal[(seed, "B")]["semantic_success"]
        for seed in range(1, 21)
    }
    output.append({
        "condition": "signal_paired_A_B",
        "endpoint": "both_ordered_answers_expected",
        "matched_trials": 20,
        "both": sum(tool_pair[s] and codex_pair[s] for s in range(1, 21)),
        "tool_less_only": sum(tool_pair[s] and not codex_pair[s] for s in range(1, 21)),
        "codex_agent_only": sum(codex_pair[s] and not tool_pair[s] for s in range(1, 21)),
        "neither": sum(not tool_pair[s] and not codex_pair[s] for s in range(1, 21)),
    })
    return output


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


def report(cells: list[dict], pairs: list[dict], efforts: list[dict], discordance: list[dict]) -> str:
    signal = {
        (row["regime"], row["stimulus_identity"]): row
        for row in cells if row["condition"] == "signal"
    }
    clean = {
        (row["regime"], row["stimulus_identity"]): row
        for row in cells if row["condition"] == "clean"
    }
    controls = {row["regime"]: row for row in cells if row["condition"] == "all_shuffled"}
    pair_by_regime = {row["regime"]: row for row in pairs}
    tool_signal_success = sum(signal[("tool_less", identity)]["semantic_success"] for identity in ("A", "B"))
    codex_signal_success = sum(signal[("codex_agent", identity)]["semantic_success"] for identity in ("A", "B"))
    lines = [
        "# Cost-truncated tool-less pilot analysis", "",
        "## Result", "",
        "The no-tool model recovered the expected ordered answer in **35/40 N=2 signal",
        "trials (87.5%)**, including both A and B answers in **16/20 equal-word-bag",
        "pairs (80.0%)**. The same 40 prompts produced 29/40 expected answers and",
        "11/20 discriminating pairs under the Codex-agent regime. All 40 clean trials",
        "succeeded in both regimes.", "",
        "This is direct behavioral evidence that shell, filesystem access, and an agentic",
        "tool loop are not required for ordered-lane recovery at N=2. It strengthens—but",
        "does not prove—the transformer-level source-separation interpretation: the two",
        "regimes also differ in system context and runtime, private reasoning was not",
        "exposed, and this was not a randomized sample of models.", "",
        "The tool-less control cohort stopped at 14/20 prompts for cost. Five returned a",
        "response and nine reached the approximately 600-second connection limit. None of",
        "the 14 produced target answer A or B; the matched Codex controls also produced no",
        "target answer. Because most tool-less controls are nonresponses, this is weak",
        "evidence about completed-response answer bias but strong evidence of an effort",
        "explosion when no intact lane exists.", "",
        "## Answer identity and success", "",
        "| regime | condition | N | stimulus | scheduled | completed | timeouts | A | B | other/no answer | exact | expected | scheduled rate [95% CI] | completed-only | final-text discovery |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in cells:
        lines.append(
            f"| {row['regime']} | {row['condition']} | {row['lanes']} | {row['stimulus_identity']} | "
            f"{row['scheduled']} | {row['completed_responses']} | {row['timeout_nonresponses']} | "
            f"{row['answer_A']} | {row['answer_B']} | {row['other_or_no_answer']} | "
            f"{row['exact_success']} | {row['semantic_success']} | {pct(row['scheduled_success_rate'])} "
            f"[{pct(row['success_ci_low'])}, {pct(row['success_ci_high'])}] | "
            f"{pct(row['completed_success_rate'])} | {row['encoding_discovered_in_final']} |"
        )
    lines += [
        "", "For all-shuffled rows, `expected` is structurally zero because there is no",
        "designated answer key; columns A and B are the relevant target-answer endpoint.", "",
        "## Paired A/B discrimination at N=2", "",
        "A pair counts only when its A stimulus produced answer A and its B stimulus",
        "produced answer B. The aggregate whitespace-delimited word bag is identical",
        "within every A/B pair.", "",
        "| regime | pairs | both expected | rate [95% CI] | A-only | B-only | neither | same-A error | same-B error |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in pairs:
        lines.append(
            f"| {row['regime']} | {row['pairs']} | {row['A_to_A_and_B_to_B']} | "
            f"{pct(row['paired_discrimination_rate'])} [{pct(row['ci_low'])}, {pct(row['ci_high'])}] | "
            f"{row['A_expected_B_not']} | {row['B_expected_A_not']} | {row['neither_expected']} | "
            f"{row['same_A_answer']} | {row['same_B_answer']} |"
        )
    lines += [
        "", "## Matched regime comparison", "",
        "| endpoint cohort | matched | both | tool-less only | Codex only | neither |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in discordance:
        lines.append(
            f"| {row['condition']} — {row['endpoint']} | {row['matched_trials']} | "
            f"{row['both']} | {row['tool_less_only']} | {row['codex_agent_only']} | {row['neither']} |"
        )
    lines += [
        "", f"At the individual-signal level, tool-less was correct on {tool_signal_success}/40",
        f"versus {codex_signal_success}/40 matched prompts. On paired discrimination it was",
        f"{pair_by_regime['tool_less']['A_to_A_and_B_to_B']}/20 versus",
        f"{pair_by_regime['codex_agent']['A_to_A_and_B_to_B']}/20. These regime differences",
        "are descriptive: the pilot was powered to detect ordered-channel behavior, not a",
        "small performance difference between runtimes.", "",
        "## Computational effort", "",
        "| regime | condition | N | scheduled | completed | timeouts | tool users | median seconds | median input* | median output* | median reasoning* | emitted reasoning items* | model turns |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in efforts:
        lines.append(
            f"| {row['regime']} | {row['condition']} | {row['lanes']} | {row['scheduled']} | "
            f"{row['completed_responses']} | {row['timeouts']} | {row['tool_using_trials']} | "
            f"{row['median_elapsed_seconds_scheduled'] or 0:.1f} | "
            f"{row['median_input_tokens_returned'] or 0:.0f} | {row['median_output_tokens_returned'] or 0:.0f} | "
            f"{row['median_reasoning_tokens_returned'] or 0:.0f} | "
            f"{row['median_emitted_reasoning_items_returned'] or 0:.0f} | {row['median_model_turns'] or 0:.0f} |"
        )
    lines += [
        "", "`*` Token and emitted-item medians use returned responses only. Nine disconnected",
        "tool-less calls have no usage object. Codex input-token counts include its runtime",
        "context and are not directly comparable to direct-API input counts.", "",
        "Clean tool-less responses used a median 215 reasoning tokens and signal responses",
        "1,678. The five completed controls used a median 24,195 reasoning tokens; all nine",
        "other controls ran for about ten minutes without a response. The matched Codex",
        "controls likewise drove tool use in 14/14 trials and much higher context/effort.",
        "The intact lane therefore changed both correctness and computational tractability.", "",
        "## Observable strategy boundary", "",
        "Every tool-less trial was one independent Responses API request with `tools: []`,",
        "`store: false`, and no prior-response context. Returned raw response objects are",
        "preserved. They contain encrypted reasoning items with empty public summaries, so",
        "their content cannot be inspected and no private-chain-of-thought claim is made.", "",
        "The constrained payload tells successful subjects to emit only the answer. Accordingly,",
        "zero final-text mentions of encoding among signal successes do not show a lack of",
        "discovery. Two completed all-shuffled outputs explicitly said that ordering had been",
        "scrambled. Strategy attribution for the tool-less successes remains indeterminate,",
        "but it cannot involve the excluded shell/filesystem/tool mechanisms.", "",
        "## Freeze, cost, and exclusions", "",
        "The stopping boundary—r0001 through r0094—was frozen before response scoring or",
        "inspection. It contains 94 scheduled trials: 40 clean, 40 signal, and 14 controls.",
        "r0095 received `credit_balance_exhausted` before inference and is preserved as an",
        "excluded invalid attempt. No later prompt was run and no timeout was retried.", "",
        "The user reported approximately $20 billed. Returned usage objects yield only a",
        "$7.5069 public-list-price lower bound; disconnected calls did not return usage",
        "objects, so the repository cannot independently reconcile the billing total.", "",
        "## Conclusion and next step", "",
        "The reduced pilot answers the important mechanistic question efficiently: at N=2,",
        "a tool-less GPT-5.6-Sol-xhigh invocation systematically followed which of two",
        "equal-multiset ordered streams was intact. That rules out both bag-of-words inference",
        "and a requirement for explicit Codex tool use as sufficient explanations.", "",
        "Do not buy the remaining 226 planned calls. If one follow-up is run later, use a",
        "small preregistered variable-stride test (for example 10 paired A/B seeds at fixed",
        "periodic N=2 versus jittered spacing), with a hard dollar cap. That directly tests",
        "whether periodic position is the exploitable cue and is more informative per dollar",
        "than filling N=4, explanation, or additional all-shuffled cells.", "",
    ]
    return "\n".join(lines)


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_chart(path: Path, title: str, labels: list[str], series: list[dict], y_max: float = 1.0) -> None:
    width, height = 900, 500
    left, right, top, bottom = 90, 30, 60, 105
    plot_width, plot_height = width - left - right, height - top - bottom
    xs = [left + i * plot_width / max(1, len(labels) - 1) for i in range(len(labels))]
    y = lambda value: top + (y_max - max(0, min(y_max, value))) / y_max * plot_height
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="30" text-anchor="middle" font-family="sans-serif" font-size="20" font-weight="600">{_escape(title)}</text>',
    ]
    for tick in range(6):
        value = y_max * tick / 5
        position = y(value)
        elements.append(f'<line x1="{left}" y1="{position:.1f}" x2="{width-right}" y2="{position:.1f}" stroke="#e5e7eb"/>')
        label = f"{100 * value:.0f}%" if y_max == 1 else f"{value:.0f}"
        elements.append(f'<text x="{left-12}" y="{position+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="12">{label}</text>')
    for index, label in enumerate(labels):
        elements.append(f'<text x="{xs[index]:.1f}" y="{height-bottom+28}" text-anchor="middle" font-family="sans-serif" font-size="12">{_escape(label)}</text>')
    for index, item in enumerate(series):
        color = COLORS[index % len(COLORS)]
        points = []
        for column, value in enumerate(item["values"]):
            if value is None:
                continue
            points.append(f"{xs[column]:.1f},{y(value):.1f}")
            elements.append(f'<circle cx="{xs[column]:.1f}" cy="{y(value):.1f}" r="5" fill="{color}"/>')
        if len(points) > 1:
            elements.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        legend_x = left + index * 220
        legend_y = height - 48
        elements.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x+24}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        elements.append(f'<text x="{legend_x+30}" y="{legend_y+4}" font-family="sans-serif" font-size="12">{_escape(item["name"])}</text>')
    elements.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(elements) + "\n")


def make_figures(cells: list[dict], pairs: list[dict], efforts: list[dict], path: Path) -> None:
    lookup = {(row["regime"], row["condition"], row["stimulus_identity"]): row for row in cells}
    write_chart(
        path / "raw-pilot-expected-answer-success.svg",
        "Expected-answer success on matched prompts",
        ["clean A", "clean B", "signal A", "signal B"],
        [{"name": regime, "values": [
            lookup[(regime, "clean", "A")]["scheduled_success_rate"],
            lookup[(regime, "clean", "B")]["scheduled_success_rate"],
            lookup[(regime, "signal", "A")]["scheduled_success_rate"],
            lookup[(regime, "signal", "B")]["scheduled_success_rate"],
        ]} for regime in ("tool_less", "codex_agent")],
    )
    pair_lookup = {row["regime"]: row for row in pairs}
    write_chart(
        path / "raw-pilot-paired-discrimination.svg",
        "Equal-word-bag paired A/B discrimination at N=2",
        ["tool-less", "Codex agent"],
        [{"name": "both ordered answers expected", "values": [
            pair_lookup["tool_less"]["paired_discrimination_rate"],
            pair_lookup["codex_agent"]["paired_discrimination_rate"],
        ]}],
    )
    effort_lookup = {(row["regime"], row["condition"]): row for row in efforts}
    write_chart(
        path / "raw-pilot-median-reasoning-tokens.svg",
        "Median reasoning tokens (returned responses)",
        ["clean", "signal N=2", "all shuffled N=2"],
        [{"name": regime, "values": [
            effort_lookup[(regime, condition)]["median_reasoning_tokens_returned"]
            for condition in ("clean", "signal", "all_shuffled")
        ]} for regime in ("tool_less", "codex_agent")],
        25000,
    )


def main() -> None:
    root = Path(__file__).resolve().parent
    results = root / "results"
    freeze = json.loads((results / "raw-model-pilot-freeze.json").read_text())
    tool = read_jsonl(results / "raw-model-pilot-trials.jsonl")
    tool_by_id = {record["neutral_id"]: record for record in tool}
    if len(tool_by_id) != len(tool):
        raise RuntimeError("duplicate tool-less neutral IDs")
    codex_all = read_jsonl(results / "trials.jsonl")
    codex = [record for record in codex_all if record["neutral_id"] in tool_by_id]
    codex_by_id = {record["neutral_id"]: record for record in codex}
    frozen_count = freeze["frozen_pilot_trials"]
    if len(tool) != frozen_count or len(codex) != frozen_count:
        raise RuntimeError("matched cohort size mismatch")
    if set(tool_by_id) != set(codex_by_id):
        raise RuntimeError("matched cohort ID sets differ")
    for trial_id in tool_by_id:
        if tool_by_id[trial_id]["prompt_sha256"] != codex_by_id[trial_id]["prompt_sha256"]:
            raise RuntimeError(f"{trial_id}: matched prompt hash differs")
    metric_all = read_jsonl(results / "trace-metrics.jsonl")
    codex_metrics = {record["neutral_id"]: record for record in metric_all if record["neutral_id"] in tool_by_id}
    if set(codex_metrics) != set(tool_by_id):
        raise RuntimeError("matched Codex trace-metric IDs differ")
    cells = cell_rows(tool, "tool_less") + cell_rows(codex, "codex_agent")
    condition_order = {"clean": 0, "signal": 1, "all_shuffled": 2}
    cells.sort(key=lambda row: (condition_order[row["condition"]], row["stimulus_identity"], row["regime"]))
    pairs = [paired_row(tool, "tool_less"), paired_row(codex, "codex_agent")]
    efforts = effort_rows(root, tool, codex, codex_metrics)
    discordance = discordance_rows(tool, codex)
    write_csv(results / "raw-model-pilot-cells.csv", cells)
    write_csv(results / "raw-model-pilot-pairs.csv", pairs)
    write_csv(results / "raw-model-pilot-effort.csv", efforts)
    write_csv(results / "raw-model-pilot-regime-discordance.csv", discordance)
    (results / "raw-model-pilot-analysis.md").write_text(report(cells, pairs, efforts, discordance))
    make_figures(cells, pairs, efforts, results / "figures")
    print(f"analyzed {len(tool)} tool-less and {len(codex)} prompt-matched Codex trials")


if __name__ == "__main__":
    main()
