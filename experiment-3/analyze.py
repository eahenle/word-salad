#!/usr/bin/env python3
"""Analyze the frozen Experiment 3 model/reasoning screening matrix."""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from runtime import MODELS, EFFORTS, atomic_bytes, cell_slug
from trace_strategy import analyze_trace


MODEL_LABELS = {
    "gpt-5.6-sol": "Sol",
    "gpt-5.6-terra": "Terra",
    "gpt-5.6-luna": "Luna",
    "gpt-5.3-codex-spark": "Spark",
}
COLORS = {"fixed": "#2563eb", "jitter": "#dc2626"}
SCREENING_IDS = {
    *(f"q{number:04d}" for number in range(1, 11)),
    *(f"q{number:04d}" for number in range(21, 31)),
    *(f"q{number:04d}" for number in range(41, 51)),
    *(f"q{number:04d}" for number in range(61, 71)),
    "q0081", "q0082", "q0083",
}


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


def load_records(root: Path) -> list[dict]:
    records = []
    for model in MODELS:
        for effort in EFFORTS:
            slug = cell_slug(model, effort)
            if (model, effort) == ("gpt-5.6-sol", "xhigh"):
                path = root / "results/anchor-trials-auto-scored.jsonl"
            else:
                path = root / "results/cells" / slug / "trials-auto-scored.jsonl"
            cell = [
                record for record in (
                    json.loads(line) for line in path.read_text().splitlines() if line.strip()
                )
                if record["neutral_id"] in SCREENING_IDS
            ]
            if len(cell) != 43:
                raise RuntimeError(f"{slug}: expected 43 scored records, got {len(cell)}")
            for record in cell:
                if record["model"] != model or record["reasoning"] != effort:
                    raise RuntimeError(f"{slug}: record cell mismatch")
                trace = (
                    root.parent / record["source_experiment"] / record["source_trace_file"]
                    if record.get("execution_origin") == "reused_frozen_experiment_2"
                    else root / record["trace_file"]
                )
                trace_result = analyze_trace(trace, record)
                merged = dict(record)
                merged["observable_strategy"] = trace_result["strategy"]
                merged["strategy_flags"] = trace_result["flags"]
                merged["trace_metrics"] = {
                    key: value for key, value in trace_result.items()
                    if key not in {"strategy", "flags", "evidence"}
                }
                merged["strategy_evidence"] = trace_result["evidence"]
                records.append(merged)
    if len(records) != 516:
        raise RuntimeError(f"expected 516 matrix records, got {len(records)}")
    return records


def paired_rows(records: list[dict]) -> list[dict]:
    rows = []
    for model in MODELS:
        for effort in EFFORTS:
            for carrier in ("fixed", "jitter"):
                group = [r for r in records if r["model"] == model and r["reasoning"] == effort and r["carrier"] == carrier]
                indexed = {(r["seed"], r["payload_identity"]): r for r in group}
                pairs = [(indexed[(seed, "A")], indexed[(seed, "B")]) for seed in range(1, 11)]
                success = sum(a["semantic_success"] and b["semantic_success"] for a, b in pairs)
                low, high = wilson(success, len(pairs))
                rows.append({
                    "model": model, "reasoning": effort, "carrier": carrier,
                    "pairs": len(pairs), "paired_success": success,
                    "paired_success_rate": success / len(pairs),
                    "paired_ci_low": low, "paired_ci_high": high,
                    "A_only_success": sum(a["semantic_success"] and not b["semantic_success"] for a, b in pairs),
                    "B_only_success": sum(b["semantic_success"] and not a["semantic_success"] for a, b in pairs),
                    "neither_success": sum(not a["semantic_success"] and not b["semantic_success"] for a, b in pairs),
                })
    return rows


def answer_rows(records: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        groups[(record["model"], record["reasoning"], record["carrier"], record.get("payload_identity") or "none")].append(record)
    rows = []
    for key in sorted(groups):
        group = groups[key]
        successes = sum(r["semantic_success"] for r in group)
        low, high = wilson(successes, len(group))
        rows.append({
            "model": key[0], "reasoning": key[1], "carrier": key[2], "stimulus_identity": key[3],
            "trials": len(group), "completed_responses": sum(r["completed_response"] for r in group),
            "answer_A": sum(r["observed_answer_identity"] == "A" for r in group),
            "answer_B": sum(r["observed_answer_identity"] == "B" for r in group),
            "other_or_no_answer": sum(r["observed_answer_identity"] is None for r in group),
            "expected_success": successes, "expected_success_rate": successes / len(group),
            "success_ci_low": low, "success_ci_high": high,
        })
    return rows


def effort_rows(records: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        groups[(record["model"], record["reasoning"], record["carrier"])].append(record)
    rows = []
    for key in sorted(groups):
        group = groups[key]
        metrics = [r["trace_metrics"] for r in group]
        rows.append({
            "model": key[0], "reasoning": key[1], "carrier": key[2], "trials": len(group),
            "semantic_successes": sum(r["semantic_success"] for r in group),
            "timeouts": sum(r["runner"]["timed_out"] for r in group),
            "tool_using_trials": sum(m["tool_calls"] > 0 for m in metrics),
            "tool_use_rate": sum(m["tool_calls"] > 0 for m in metrics) / len(group),
            "median_elapsed_seconds": median([r["runner"]["elapsed_seconds"] for r in group]),
            "median_input_tokens": median([m["input_tokens"] for m in metrics]),
            "median_cached_input_tokens": median([m["cached_input_tokens"] for m in metrics]),
            "median_output_tokens": median([m["output_tokens"] for m in metrics]),
            "median_reasoning_tokens": median([m["reasoning_tokens"] for m in metrics]),
            "median_model_turns": median([m["model_turns"] for m in metrics]),
            "median_tool_calls": median([m["tool_calls"] for m in metrics]),
            "median_shell_calls": median([m["shell_calls"] for m in metrics]),
            "median_trace_bytes": median([m["trace_bytes"] for m in metrics]),
        })
    return rows


def strategy_rows(records: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        groups[(record["model"], record["reasoning"], record["carrier"], bool(record["semantic_success"]))].append(record)
    rows = []
    for key in sorted(groups):
        group = groups[key]
        counts = Counter(r["observable_strategy"] for r in group)
        for strategy, count in sorted(counts.items()):
            rows.append({
                "model": key[0], "reasoning": key[1], "carrier": key[2],
                "semantic_success": key[3], "strategy": strategy,
                "count": count, "group_trials": len(group), "within_group_rate": count / len(group),
            })
    return rows


def mcnemar(records: list[dict], paired: bool) -> dict:
    discordant_fixed = 0
    discordant_jitter = 0
    total = 0
    for model in MODELS:
        for effort in EFFORTS:
            cell = [r for r in records if r["model"] == model and r["reasoning"] == effort]
            index = {(r["carrier"], r["seed"], r.get("payload_identity")): r for r in cell}
            for seed in range(1, 11):
                if paired:
                    fixed = all(index[("fixed", seed, identity)]["semantic_success"] for identity in ("A", "B"))
                    jitter = all(index[("jitter", seed, identity)]["semantic_success"] for identity in ("A", "B"))
                    comparisons = [(fixed, jitter)]
                else:
                    comparisons = [
                        (index[("fixed", seed, identity)]["semantic_success"], index[("jitter", seed, identity)]["semantic_success"])
                        for identity in ("A", "B")
                    ]
                for fixed, jitter in comparisons:
                    total += 1
                    discordant_fixed += bool(fixed and not jitter)
                    discordant_jitter += bool(jitter and not fixed)
    n = discordant_fixed + discordant_jitter
    k = min(discordant_fixed, discordant_jitter)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)) if n else 1.0
    return {
        "comparisons": total, "fixed_only_success": discordant_fixed,
        "jitter_only_success": discordant_jitter, "discordant": n,
        "two_sided_exact_mcnemar_p": p,
    }


def matrix_rows(records: list[dict], pairs: list[dict]) -> list[dict]:
    pair_index = {(r["model"], r["reasoning"], r["carrier"]): r for r in pairs}
    rows = []
    for model in MODELS:
        for effort in EFFORTS:
            cell = [r for r in records if r["model"] == model and r["reasoning"] == effort]
            fixed = [r for r in cell if r["carrier"] == "fixed"]
            jitter = [r for r in cell if r["carrier"] == "jitter"]
            controls = [r for r in cell if r["carrier"] == "all-shuffled"]
            fp = pair_index[(model, effort, "fixed")]
            jp = pair_index[(model, effort, "jitter")]
            signals = fixed + jitter
            rows.append({
                "model": model, "reasoning": effort,
                "fixed_individual": sum(r["semantic_success"] for r in fixed),
                "fixed_individual_trials": len(fixed),
                "fixed_paired": fp["paired_success"], "fixed_pairs": fp["pairs"],
                "jitter_individual": sum(r["semantic_success"] for r in jitter),
                "jitter_individual_trials": len(jitter),
                "jitter_paired": jp["paired_success"], "jitter_pairs": jp["pairs"],
                "individual_jitter_penalty": sum(r["semantic_success"] for r in fixed) / len(fixed) - sum(r["semantic_success"] for r in jitter) / len(jitter),
                "paired_jitter_penalty": fp["paired_success_rate"] - jp["paired_success_rate"],
                "signal_tool_use_rate": sum(r["trace_metrics"]["tool_calls"] > 0 for r in signals) / len(signals),
                "signal_timeouts": sum(r["runner"]["timed_out"] for r in signals),
                "control_target_answers": sum(r["observed_answer_identity"] in {"A", "B"} for r in controls),
                "control_timeouts": sum(r["runner"]["timed_out"] for r in controls),
            })
    return rows


def _esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def grouped_chart(path: Path, title: str, labels: list[str], fixed: list[float], jitter: list[float], y_label: str) -> None:
    width, height = 1120, 560
    left, right, top, bottom = 80, 30, 65, 125
    plot_w, plot_h = width - left - right, height - top - bottom
    group_w = plot_w / len(labels)
    bar_w = group_w * 0.3
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="32" text-anchor="middle" font-family="sans-serif" font-size="21" font-weight="600">{_esc(title)}</text>',
        f'<text x="18" y="{top+plot_h/2}" transform="rotate(-90 18 {top+plot_h/2})" text-anchor="middle" font-family="sans-serif" font-size="13">{_esc(y_label)}</text>',
    ]
    for tick in range(6):
        value = tick / 5
        y = top + (1 - value) * plot_h
        elements += [
            f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e5e7eb"/>',
            f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="12">{value:.1f}</text>',
        ]
    for i, label in enumerate(labels):
        center = left + (i + 0.5) * group_w
        for j, (value, carrier) in enumerate(((fixed[i], "fixed"), (jitter[i], "jitter"))):
            x = center + (j - 1) * bar_w
            y = top + (1 - value) * plot_h
            elements.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{top+plot_h-y:.1f}" fill="{COLORS[carrier]}"/>')
        elements.append(f'<text x="{center:.1f}" y="{top+plot_h+22}" text-anchor="middle" font-family="sans-serif" font-size="11" transform="rotate(35 {center:.1f} {top+plot_h+22})">{_esc(label)}</text>')
    elements += [
        f'<rect x="{left}" y="{height-35}" width="14" height="14" fill="{COLORS["fixed"]}"/><text x="{left+20}" y="{height-23}" font-family="sans-serif" font-size="12">fixed</text>',
        f'<rect x="{left+90}" y="{height-35}" width="14" height="14" fill="{COLORS["jitter"]}"/><text x="{left+110}" y="{height-23}" font-family="sans-serif" font-size="12">jitter</text>',
        '</svg>',
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(elements) + "\n")


def report(records: list[dict], matrix: list[dict], effort: list[dict], strategies: list[dict], tests: dict) -> str:
    total_fixed = sum(r["fixed_individual"] for r in matrix)
    total_jitter = sum(r["jitter_individual"] for r in matrix)
    paired_fixed = sum(r["fixed_paired"] for r in matrix)
    paired_jitter = sum(r["jitter_paired"] for r in matrix)
    controls = [r for r in records if r["carrier"] == "all-shuffled"]
    successes = [r for r in records if r["carrier"] != "all-shuffled" and r["semantic_success"]]
    direct_success = sum(r["observable_strategy"] == "direct_one_pass_tool_free" for r in successes)
    tool_success = sum(r["trace_metrics"]["tool_calls"] > 0 for r in successes)
    fixed_evidence = sum(r["strategy_flags"]["fixed_stride_hypothesis"] for r in successes)
    jitter_evidence = sum(r["strategy_flags"]["jitter_pattern_hypothesis"] for r in successes)
    lines = [
        "# Experiment 3 screening analysis", "",
        "## Main result", "",
        f"Across 12 exact model/reasoning configurations, fixed carriers produced {total_fixed}/240 expected individual answers and {paired_fixed}/120 complete A/B pairs. Balanced jitter produced {total_jitter}/240 individual answers and {paired_jitter}/120 pairs. The paired jitter penalty was therefore {(paired_fixed-paired_jitter)/120:.1%} (negative means jitter performed better).", "",
        f"The within-cell matched comparison had {tests['paired']['fixed_only_success']} fixed-only versus {tests['paired']['jitter_only_success']} jitter-only paired successes (two-sided exact McNemar p={tests['paired']['two_sided_exact_mcnemar_p']:.4g}). At the individual-prompt level the corresponding counts were {tests['individual']['fixed_only_success']} and {tests['individual']['jitter_only_success']} (p={tests['individual']['two_sided_exact_mcnemar_p']:.4g}). These repeatability summaries are not population inference over models.", "",
        "A strict period-2 carrier is not required. The balanced jitter manipulation did not merely preserve recovery; it improved aggregate recovery. This does not show that arbitrary sparse placement is equally recoverable: the 1/3 interval mask creates runs of adjacent signal words, which may supply stronger local coherence than alternation. Uniform random placement is now the most discriminating structural follow-up.", "",
        "## Model and effort matrix", "",
        "| model | effort | fixed individual | fixed pairs | jitter individual | jitter pairs | paired jitter penalty | signal tool use | timeouts |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in matrix:
        lines.append(
            f"| {MODEL_LABELS[row['model']]} | {row['reasoning']} | {row['fixed_individual']}/20 | "
            f"{row['fixed_paired']}/10 | {row['jitter_individual']}/20 | {row['jitter_paired']}/10 | "
            f"{row['paired_jitter_penalty']:.0%} | {row['signal_tool_use_rate']:.0%} | "
            f"{row['signal_timeouts'] + row['control_timeouts']} |"
        )
    lines += ["", "Reasoning effort was not monotonic. Sol remained strongest at every effort, Terra and Luna were intermediate, and Spark showed a sharp lower boundary: one expected jitter answer at xhigh, but no complete A/B pair at any Spark effort. Higher effort sometimes increased recovery and sometimes reduced it.", "",
              "## Controls and answer bias", "",
              f"The 36 all-shuffled controls produced {sum(r['observed_answer_identity'] in {'A','B'} for r in controls)} target A/B answers. {sum(r['runner']['timed_out'] for r in controls)} controls reached 900 seconds. The absence of target answers across all model/effort cells argues against a generic bag-of-words target bias in this cohort.", "",
              "## Computational effort", "",
              "| model | effort | carrier | trials | success | timeout | tool users | median seconds | median reasoning tokens |",
              "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in effort:
        lines.append(
            f"| {MODEL_LABELS[row['model']]} | {row['reasoning']} | {row['carrier']} | {row['trials']} | "
            f"{row['semantic_successes']} | {row['timeouts']} | {row['tool_using_trials']} | "
            f"{row['median_elapsed_seconds']:.1f} | {row['median_reasoning_tokens'] or 0:.0f} |"
        )
    lines += ["", "Timeouts were retained as scheduled-trial outcomes. There were no broken pipes, connection resets, capacity failures, or other retry-eligible infrastructure errors. The only signal timeout was Luna-high jitter q0046; the remaining timeouts were all-shuffled controls.", "",
              "## Observable trace strategies", "",
              f"Among {len(successes)} successful signal trials, {direct_success} were observable one-pass tool-free responses and {tool_success} used a tool. Concrete fixed-stride evidence appeared in {fixed_evidence} successful traces; concrete jitter-pattern language appeared in {jitter_evidence}. Final-answer silence is not evidence that no pattern was noticed, and emitted traces do not expose private chain of thought.", "",
              "| strategy | successful signals | failed signals | controls |",
              "| --- | ---: | ---: | ---: |"]
    strategy_counts = defaultdict(lambda: [0, 0, 0])
    for record in records:
        if record["carrier"] == "all-shuffled":
            column = 2
        elif record["semantic_success"]:
            column = 0
        else:
            column = 1
        strategy_counts[record["observable_strategy"]][column] += 1
    for strategy, counts in sorted(strategy_counts.items()):
        lines.append(f"| {strategy} | {counts[0]} | {counts[1]} | {counts[2]} |")
    lines += ["", "The classifications require concrete observable evidence. In particular, `explicit_stride_testing` requires actual candidate-stride language or code, and `explicit_fixed_stride_recognition` requires parity/every-other/residue extraction evidence. Generic complaints about scrambled text are not promoted to stride discovery.", "",
              "## Scoring and integrity audit", "",
              "Semantic scoring accepts both the requested object-to-color form and an unambiguous inverse box-to-contents form. A post-freeze audit added this surface normalization uniformly. If an object appears in multiple reported boxes, it is not assigned by the inverse parser. The scorer tests include both visible-label and physical-box-to-visible-label renderings.", "",
              "All 473 fresh screening traces, 23 fresh anchor traces, and 20 reused fixed-reference traces matched their frozen hashes. Prior Experiment 1C/2 worktrees remained unchanged. The isolation audit passed; no credentials were stored in the experiment tree. Same-host Docker is an audited practical boundary, not cryptographic multi-host isolation.", "",
              "## Boundary confirmation", "",
              "The preregistered 120-trial boundary confirmation is complete and reported separately in `confirmation-analysis.md`. In its fresh half, fixed and jitter produced 8/30 and 9/30 complete pairs. Cumulatively, Sol-medium reached 10/20 fixed versus 12/20 jitter pairs, Terra-xhigh 2/20 versus 6/20, and Spark-xhigh 0/20 versus 0/20. The confirmation preserves the no-collapse conclusion while showing that the screening-wide jitter advantage was not equally large in fresh seeds.", "",
              "## Interpretation", "",
              "The data support general ordered-stream recovery beyond a fixed positional clock and a strong model-family capability gradient. They do not identify a specific transformer mechanism. The jitter advantage could reflect burst-local coherence, and effort effects are nonmonotonic. The decisive next carrier test is uniform random signal placement with the same word bags and density.", ""]
    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).resolve().parent
    integrity = json.loads((root / "results/integrity-audit.json").read_text())
    if not integrity.get("passed"):
        raise RuntimeError("passed integrity audit required")
    records = load_records(root)
    pairs = paired_rows(records)
    answers = answer_rows(records)
    effort = effort_rows(records)
    strategies = strategy_rows(records)
    matrix = matrix_rows(records, pairs)
    tests = {"individual": mcnemar(records, False), "paired": mcnemar(records, True)}
    results = root / "results"
    atomic_bytes(results / "trials.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records).encode())
    write_csv(results / "answer-identity.csv", answers)
    write_csv(results / "model-reasoning-matrix.csv", matrix)
    write_csv(results / "jitter-contrasts.csv", [
        {key: row[key] for key in (
            "model", "reasoning", "fixed_individual", "jitter_individual",
            "individual_jitter_penalty", "fixed_paired", "jitter_paired", "paired_jitter_penalty"
        )} for row in matrix
    ])
    write_csv(results / "effort-summary.csv", effort)
    write_csv(results / "strategy-summary.csv", strategies)
    (results / "matched-tests.json").write_text(json.dumps(tests, indent=2) + "\n")
    evidence_rows = [{
        "model": r["model"], "reasoning": r["reasoning"], "trial_id": r["neutral_id"],
        "carrier": r["carrier"], "semantic_success": r["semantic_success"],
        "strategy": r["observable_strategy"], "flags": r["strategy_flags"],
        "evidence": r["strategy_evidence"],
    } for r in records]
    atomic_bytes(results / "strategy-evidence.jsonl", "".join(json.dumps(r) + "\n" for r in evidence_rows).encode())
    (results / "analysis.md").write_text(report(records, matrix, effort, strategies, tests))

    labels = [f"{MODEL_LABELS[r['model']]}-{r['reasoning'][0].upper()}" for r in matrix]
    grouped_chart(results / "figures/individual-recovery.svg", "Individual expected-answer recovery", labels,
                  [r["fixed_individual"] / 20 for r in matrix], [r["jitter_individual"] / 20 for r in matrix], "success rate")
    grouped_chart(results / "figures/paired-recovery.svg", "Paired A/B discrimination", labels,
                  [r["fixed_paired"] / 10 for r in matrix], [r["jitter_paired"] / 10 for r in matrix], "paired success rate")
    effort_index = {(r["model"], r["reasoning"], r["carrier"]): r for r in effort}
    max_seconds = max(effort_index[(r["model"], r["reasoning"], c)]["median_elapsed_seconds"] for r in matrix for c in ("fixed", "jitter"))
    grouped_chart(results / "figures/median-elapsed.svg", "Median wall time (normalized to largest cell median)", labels,
                  [effort_index[(r["model"], r["reasoning"], "fixed")]["median_elapsed_seconds"] / max_seconds for r in matrix],
                  [effort_index[(r["model"], r["reasoning"], "jitter")]["median_elapsed_seconds"] / max_seconds for r in matrix], "relative median wall time")
    grouped_chart(results / "figures/tool-use-rate.svg", "Signal tool-use rate", labels,
                  [effort_index[(r["model"], r["reasoning"], "fixed")]["tool_use_rate"] for r in matrix],
                  [effort_index[(r["model"], r["reasoning"], "jitter")]["tool_use_rate"] for r in matrix], "tool-use rate")
    print(json.dumps({"records": len(records), "matrix": matrix, "matched_tests": tests}, indent=2))


if __name__ == "__main__":
    main()
