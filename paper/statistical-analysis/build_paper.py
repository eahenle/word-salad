#!/usr/bin/env python3
"""Build publication tables, figures, and integrity metadata from frozen results."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
import subprocess
from pathlib import Path


PAPER = Path(__file__).resolve().parents[1]
REPO = PAPER.parent
TABLES = PAPER / "results-tables"
FIGURES = PAPER / "figures"
PROVENANCE = PAPER / "provenance"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict]) -> None:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(stream.getvalue())


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if not trials:
        return 0.0, 0.0
    rate = successes / trials
    denominator = 1 + z * z / trials
    center = (rate + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt(rate * (1 - rate) / trials + z * z / (4 * trials * trials)) / denominator
    return center - margin, center + margin


def metric_row(study: str, endpoint: str, successes: int, trials: int, role: str) -> dict:
    low, high = wilson(successes, trials)
    return {
        "study": study,
        "endpoint": endpoint,
        "successes": successes,
        "trials": trials,
        "rate": round(successes / trials, 6),
        "wilson_95_low": round(low, 6),
        "wilson_95_high": round(high, 6),
        "manuscript_role": role,
    }


def core_evidence() -> list[dict]:
    rows = [
        metric_row("Experiment 2", "N=2 expected individuals", 57, 80, "core"),
        metric_row("Experiment 2", "N=2 complete A/B pairs", 19, 40, "core"),
        metric_row("Experiment 2", "N=4 expected individuals", 33, 80, "core"),
        metric_row("Experiment 2", "N=4 complete A/B pairs", 8, 40, "core"),
        metric_row("Experiment 2", "all-shuffled target answers", 0, 80, "control"),
        metric_row("Experiment 2 tool-less pilot", "N=2 expected individuals", 35, 40, "core replication"),
        metric_row("Experiment 2 tool-less pilot", "N=2 complete A/B pairs", 16, 20, "core replication"),
        metric_row("Experiment 3", "fixed expected individuals", 69, 240, "carrier characterization"),
        metric_row("Experiment 3", "fixed complete A/B pairs", 17, 120, "carrier characterization"),
        metric_row("Experiment 3", "jitter expected individuals", 95, 240, "carrier characterization"),
        metric_row("Experiment 3", "jitter complete A/B pairs", 31, 120, "carrier characterization"),
        metric_row("Experiment 4A", "uniform expected individuals", 46, 80, "core"),
        metric_row("Experiment 4A", "uniform complete A/B pairs", 18, 40, "core"),
        metric_row("Experiment 4A", "all-shuffled target answers", 0, 10, "control"),
        metric_row("Experiment 6 v2", "clean exact execution", 40, 40, "instrument validation"),
        metric_row("Experiment 6 v2", "scrambled target false positives", 2, 10, "failed control"),
    ]
    return rows


def configuration_rows() -> list[dict]:
    return [
        {"study": "Experiment 1C", "model": "gpt-5.6-sol", "reasoning": "xhigh", "new_trials": 320, "runtime": "Docker Codex", "primary_conditions": "4 surfaces x signal/shuffled x N=1,2,4,8", "status": "frozen validated"},
        {"study": "Experiment 2", "model": "gpt-5.6-sol", "reasoning": "xhigh", "new_trials": 320, "runtime": "Docker Codex", "primary_conditions": "clean/signal/shuffled; constrained/explanation; N=1,2,4", "status": "frozen validated"},
        {"study": "Experiment 2 tool-less", "model": "gpt-5.6-sol", "reasoning": "xhigh", "new_trials": 94, "runtime": "direct tool-less pilot", "primary_conditions": "cost-truncated matched pilot", "status": "frozen cost-truncated"},
        {"study": "Experiment 3", "model": "Sol/Terra/Luna/Spark", "reasoning": "medium/high/xhigh", "new_trials": 616, "runtime": "Docker Codex", "primary_conditions": "fixed/jitter + small controls + confirmation", "status": "frozen validated"},
        {"study": "Experiment 4A", "model": "Sol-medium; Terra-xhigh", "reasoning": "declared per cell", "new_trials": 90, "runtime": "Docker Codex", "primary_conditions": "uniform-random signal + shuffled controls", "status": "frozen validated"},
        {"study": "Experiment 4C/4C.1", "model": "gpt-5.6-sol", "reasoning": "medium", "new_trials": 21, "runtime": "no-tool Docker", "primary_conditions": "coherent/decohered low-density foreground", "status": "frozen negative"},
        {"study": "Experiment 5 balanced density", "model": "gpt-5.6-sol", "reasoning": "medium", "new_trials": 36, "runtime": "no-tool Docker", "primary_conditions": "7.5/12.5/25/50% A/B/scrambled", "status": "frozen control stop"},
        {"study": "Experiment 6 v1", "model": "gpt-5.6-sol", "reasoning": "medium", "new_trials": 40, "runtime": "no-tool Docker", "primary_conditions": "clean task validation", "status": "frozen task failure"},
        {"study": "Experiment 6 v2", "model": "gpt-5.6-sol", "reasoning": "medium", "new_trials": 50, "runtime": "no-tool Docker", "primary_conditions": "40 clean + 10 scrambled", "status": "frozen control stop"},
    ]


def invalidation_rows() -> list[dict]:
    return [
        {"study": "Experiment 1 original", "artifact": "historical baseline", "issue": "same-host, weaker instrumentation/isolation", "handling": "preserved; not primary hardened evidence"},
        {"study": "Experiment 1B", "artifact": "same-host replication", "issue": "same-host contamination risk", "handling": "tagged invalidated; replaced by Experiment 1C"},
        {"study": "Experiment 2", "artifact": "9 initial attempts", "issue": "pre-inference account usage cap", "handling": "archived and exact prompts rerun after capacity probe"},
        {"study": "Experiment 2 tool-less", "artifact": "r0095 and later", "issue": "credit exhausted", "handling": "r0095 excluded pre-inference; cost-truncated stop frozen"},
        {"study": "Experiment 4B", "artifact": "runtime/method pilots", "issue": "runtime and overt-semantic confounds", "handling": "preserved under invalidated directories; canary claim abandoned"},
        {"study": "Experiment 5 balanced density", "artifact": "2 d250 attempts", "issue": "pre-response expired/reused refresh token", "handling": "archived; only those exact prompts rerun"},
        {"study": "Experiment 6 v1", "artifact": "five-symbol rotation task", "issue": "0/40 clean execution", "handling": "preregistered gate stopped instrument; no controls/interference run"},
        {"study": "Experiment 6 v2", "artifact": "five-symbol swap task", "issue": "2/10 scrambled controls hit target A", "handling": "preregistered gate stopped instrument; no interference run"},
    ]


def frozen_tag_rows() -> list[dict]:
    tags = subprocess.check_output(
        ["git", "tag", "--list", "experiment-*"], cwd=REPO, text=True
    ).splitlines()
    rows = []
    for tag in sorted(tags):
        commit = subprocess.check_output(
            ["git", "rev-list", "-n", "1", tag], cwd=REPO, text=True
        ).strip()
        subject = subprocess.check_output(
            ["git", "show", "-s", "--format=%s", commit], cwd=REPO, text=True
        ).strip()
        rows.append({"tag": tag, "commit": commit, "commit_subject": subject})
    return rows


def runtime_image_rows() -> list[dict]:
    return [
        {
            "studies": "Experiments 1C, 2, 3, 4A",
            "image": "sha256:883e4d8d659d28c25d2473c0dec9ff43d1bafb7ce3920ada270627df3c202402",
            "role": "hardened Docker Codex subject",
            "source": "experiment-3/frozen-references.json",
        },
        {
            "studies": "Experiments 4C, 4C.1, 5, 6",
            "image": "sha256:e04e78a7926fc489536fe595073b58888238bc4107a6fd5281047432031627da",
            "role": "audited clean no-tool Docker subject",
            "source": "experiment-4/context-audit/clean-build/build-manifest.json",
        },
    ]


def esc(value: object) -> str:
    return html.escape(str(value))


def svg_start(width: int, height: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Inter,Arial,sans-serif;fill:#1f2937}.title{font-size:24px;font-weight:700}.axis{font-size:12px;fill:#4b5563}.label{font-size:14px}.value{font-size:13px;font-weight:700}</style>',
        f'<text class="title" x="{width / 2}" y="34" text-anchor="middle">{esc(title)}</text>',
    ]


def bar_chart(
    path: Path,
    title: str,
    labels: list[str],
    values: list[float],
    notes: list[str],
    colors: list[str] | None = None,
    intervals: list[tuple[float, float]] | None = None,
    tick_labels: list[str] | None = None,
) -> None:
    width, height = 980, 110 + 62 * len(labels)
    left, right, top = 270, 80, 70
    plot = width - left - right
    colors = colors or ["#2563eb"] * len(labels)
    tick_labels = tick_labels or [f"{tick * 20}%" for tick in range(6)]
    if len(tick_labels) != 6:
        raise ValueError("tick_labels must contain six entries")
    out = svg_start(width, height, title)
    for tick in range(0, 6):
        x = left + plot * tick / 5
        out.append(f'<line x1="{x}" y1="{top - 5}" x2="{x}" y2="{height - 34}" stroke="#e5e7eb"/>')
        out.append(f'<text class="axis" x="{x}" y="{height - 14}" text-anchor="middle">{esc(tick_labels[tick])}</text>')
    for index, (label, value, note, color) in enumerate(zip(labels, values, notes, colors)):
        y = top + index * 62
        label_value = value
        out.append(f'<text class="label" x="{left - 12}" y="{y + 20}" text-anchor="end">{esc(label)}</text>')
        out.append(f'<rect x="{left}" y="{y}" width="{plot * value}" height="28" rx="3" fill="{color}"/>')
        if intervals:
            low, high = intervals[index]
            label_value = max(value, high)
            x_low, x_high = left + plot * low, left + plot * high
            out.append(f'<line x1="{x_low}" y1="{y + 14}" x2="{x_high}" y2="{y + 14}" stroke="#111827" stroke-width="2"/>')
            out.append(f'<line x1="{x_low}" y1="{y + 8}" x2="{x_low}" y2="{y + 20}" stroke="#111827" stroke-width="2"/>')
            out.append(f'<line x1="{x_high}" y1="{y + 8}" x2="{x_high}" y2="{y + 20}" stroke="#111827" stroke-width="2"/>')
        out.append(f'<text class="value" x="{left + plot * label_value + 8}" y="{y + 20}">{esc(note)}</text>')
    out.append('</svg>')
    path.write_text("\n".join(out) + "\n")


def figure_1() -> None:
    width, height = 1080, 520
    out = svg_start(width, height, "Equal-bag ordered-channel construction")
    boxes = [
        (50, 80, "Payload A", "same words; operation order A", "#dbeafe"),
        (50, 200, "Payload B", "same words; operation order B", "#ede9fe"),
        (400, 80, "Carrier mask", "fixed, jitter, or uniformly random", "#ecfccb"),
        (400, 200, "Matched interference", "same distractor words and positions", "#fef3c7"),
        (760, 140, "Stimulus", "identical aggregate word bag", "#f3f4f6"),
    ]
    for x, y, head, body, fill in boxes:
        out.append(f'<rect x="{x}" y="{y}" width="270" height="82" rx="10" fill="{fill}" stroke="#64748b"/>')
        out.append(f'<text x="{x + 135}" y="{y + 30}" text-anchor="middle" font-size="17" font-weight="700">{esc(head)}</text>')
        out.append(f'<text x="{x + 135}" y="{y + 56}" text-anchor="middle" font-size="13">{esc(body)}</text>')
    for y in (121, 241):
        out.append(f'<path d="M 320 {y} C 350 {y}, 360 140, 400 140" fill="none" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)"/>')
    out.append('<path d="M 670 121 C 710 121, 710 181, 760 181" fill="none" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)"/>')
    out.append('<path d="M 670 241 C 710 241, 710 181, 760 181" fill="none" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)"/>')
    out.append('<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#64748b"/></marker></defs>')
    out.append('<text x="540" y="345" text-anchor="middle" font-size="18" font-weight="700">Primary paired endpoint</text>')
    out.append('<text x="540" y="382" text-anchor="middle" font-size="16">A stimulus → answer A  AND  B stimulus → answer B</text>')
    out.append('<text x="540" y="425" text-anchor="middle" font-size="14">Shuffled controls preserve lexical content but contain no intact ordered task.</text>')
    out.append('</svg>')
    (FIGURES / "figure-1-construction.svg").write_text("\n".join(out) + "\n")


def figure_1b() -> None:
    prompt_path = REPO / "experiment-2/prompts/constrained/r0041.txt"
    expected_hash = "460f02401e1f2ffe65aa4588b291ceb6590c27082370a18feb14c7251c2449ef"
    assert hashlib.sha256(prompt_path.read_bytes()).hexdigest() == expected_hash
    words = prompt_path.read_text().split()
    assert len(words) == 322
    excerpt = words[:48]
    signal = excerpt[0::2]
    width, height = 1180, 720
    out = svg_start(width, height, "What the subject saw: a frozen Experiment 2 excerpt")
    out.append('<text class="axis" x="590" y="62" text-anchor="middle">Trial r0041 · N=2 · signal phase 0 · first 48 of 322 words</text>')
    out.append('<rect x="38" y="82" width="1104" height="350" rx="10" fill="#f8fafc" stroke="#cbd5e1"/>')
    out.append('<text x="60" y="112" font-size="14" font-weight="700">Raw prompt excerpt</text>')
    for index, word in enumerate(excerpt):
        row, column = divmod(index, 8)
        x, y = 60 + column * 136, 153 + row * 44
        signal_word = index % 2 == 0
        if signal_word:
            out.append(f'<rect x="{x - 5}" y="{y - 20}" width="{max(48, len(word) * 9 + 10)}" height="27" rx="4" fill="#dbeafe"/>')
        color = "#1d4ed8" if signal_word else "#64748b"
        weight = "700" if signal_word else "400"
        out.append(f'<text x="{x}" y="{y}" font-family="ui-monospace,monospace" font-size="15" font-weight="{weight}" fill="{color}">{esc(word)}</text>')
    out.append('<rect x="55" y="392" width="18" height="13" rx="2" fill="#dbeafe"/>')
    out.append('<text class="axis" x="82" y="403">highlight added for explanation; subjects received plain, unmarked text</text>')
    out.append('<path d="M590 442 L590 476" stroke="#64748b" stroke-width="2" marker-end="url(#arrow-real)"/>')
    out.append('<defs><marker id="arrow-real" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#64748b"/></marker></defs>')
    out.append('<rect x="38" y="488" width="1104" height="162" rx="10" fill="#eff6ff" stroke="#93c5fd"/>')
    out.append('<text x="60" y="520" font-size="14" font-weight="700">Highlighted positions extracted in order</text>')
    for row in range(2):
        line = " ".join(signal[row * 12 : (row + 1) * 12])
        out.append(f'<text x="60" y="{558 + row * 34}" font-family="ui-monospace,monospace" font-size="16" fill="#1e3a8a">{esc(line)}</text>')
    out.append(f'<text class="axis" x="60" y="634">Source SHA-256: {expected_hash}</text>')
    out.append('</svg>')
    (FIGURES / "figure-1b-real-stimulus.svg").write_text("\n".join(out) + "\n")


def figure_3(carrier: list[dict[str, str]]) -> None:
    labels, values, notes, colors, intervals = [], [], [], [], []
    palette = {"fixed": "#64748b", "jitter": "#f59e0b", "uniform": "#2563eb"}
    for model in ("gpt-5.6-sol", "gpt-5.6-terra"):
        for carrier_name in ("fixed", "jitter", "uniform"):
            row = next(item for item in carrier if item["model"] == model and item["carrier"] == carrier_name)
            short = "Sol-medium" if model.endswith("sol") else "Terra-xhigh"
            labels.append(f"{short} · {carrier_name}")
            values.append(float(row["paired_rate"]))
            notes.append(f"{row['paired_success']}/{row['pairs']}")
            colors.append(palette[carrier_name])
            intervals.append((float(row["paired_ci_low"]), float(row["paired_ci_high"])))
    bar_chart(
        FIGURES / "figure-3-carrier-geometry.svg",
        "Paired A/B recovery across carrier geometry",
        labels,
        values,
        notes,
        colors,
        intervals,
    )


def figure_4(matrix: list[dict[str, str]]) -> None:
    width, height = 980, 560
    out = svg_start(width, height, "Experiment 3: paired recovery by model, effort, and carrier")
    models = ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.3-codex-spark"]
    efforts = ["medium", "high", "xhigh"]
    carriers = ["fixed", "jitter"]
    label = {"gpt-5.6-sol": "Sol", "gpt-5.6-terra": "Terra", "gpt-5.6-luna": "Luna", "gpt-5.3-codex-spark": "Spark"}
    for panel, carrier in enumerate(carriers):
        x0 = 125 + panel * 445
        out.append(f'<text x="{x0 + 180}" y="78" text-anchor="middle" font-size="18" font-weight="700">{carrier}</text>')
        for col, effort in enumerate(efforts):
            out.append(f'<text class="axis" x="{x0 + col * 105 + 52}" y="108" text-anchor="middle">{effort}</text>')
        for row_index, model in enumerate(models):
            y = 125 + row_index * 88
            out.append(f'<text class="label" x="{x0 - 12}" y="{y + 34}" text-anchor="end">{label[model]}</text>')
            record = next(item for item in matrix if item["model"] == model)
            for col, effort in enumerate(efforts):
                current = next(item for item in matrix if item["model"] == model and item["reasoning"] == effort)
                successes = int(current[f"{carrier}_paired"])
                pairs = int(current[f"{carrier}_pairs"])
                rate = successes / pairs
                blue = int(245 - 140 * rate)
                fill = f"rgb({blue},{blue + 5},{245})"
                x = x0 + col * 105
                out.append(f'<rect x="{x}" y="{y}" width="92" height="58" rx="5" fill="{fill}" stroke="#cbd5e1"/>')
                out.append(f'<text class="value" x="{x + 46}" y="{y + 34}" text-anchor="middle">{successes}/{pairs}</text>')
    out.append('<text class="axis" x="490" y="520" text-anchor="middle">Darker cells indicate higher paired success. Screening cohort; exact prompts matched across configurations.</text>')
    out.append('</svg>')
    (FIGURES / "figure-4-model-effort-matrix.svg").write_text("\n".join(out) + "\n")


def figure_5(effort: list[dict[str, str]]) -> None:
    wanted = [
        ("clean N=1", "clean", "1"),
        ("signal N=2", "signal", "2"),
        ("signal N=4", "signal", "4"),
        ("shuffled N=2", "all_shuffled", "2"),
        ("shuffled N=4", "all_shuffled", "4"),
    ]
    labels, values, notes = [], [], []
    max_log = 5
    for display, condition, lanes in wanted:
        row = next(item for item in effort if item["arm"] == "constrained" and item["condition"] == condition and item["lanes"] == lanes)
        tokens = float(row["median_reasoning_tokens"])
        labels.append(display)
        values.append(math.log10(max(tokens, 1)) / max_log)
        notes.append(f"{tokens:,.0f} median tokens")
    bar_chart(
        FIGURES / "figure-5-computational-effort.svg",
        "Experiment 2 observable reasoning effort (log-scaled bars)",
        labels,
        values,
        notes,
        ["#10b981", "#2563eb", "#2563eb", "#dc2626", "#dc2626"],
        tick_labels=["1", "10", "100", "1k", "10k", "100k tokens"],
    )


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    PROVENANCE.mkdir(parents=True, exist_ok=True)
    carrier = read_csv(REPO / "experiment-4/uniform/results/carrier-comparison.csv")
    matrix = read_csv(REPO / "experiment-3/results/model-reasoning-matrix.csv")
    effort2 = read_csv(REPO / "experiment-2/results/effort-summary.csv")
    core = core_evidence()
    assert next(row for row in core if row["study"] == "Experiment 4A" and row["endpoint"] == "uniform expected individuals")["successes"] == 46
    assert sum(int(row["paired_success"]) for row in carrier if row["carrier"] == "uniform") == 18
    assert sum(int(row["individual_success"]) for row in carrier if row["carrier"] == "uniform") == 46
    assert json.loads((REPO / "experiment-6/five-symbol-v2/results/clean-gate.json").read_text())["aggregate_normalized_exact"] == 40
    assert json.loads((REPO / "experiment-6/five-symbol-v2/results/scrambled-gate.json").read_text())["target_sequence_selections"] == 2
    write_csv(TABLES / "core-evidence.csv", core)
    write_csv(TABLES / "experiment-configurations.csv", configuration_rows())
    write_csv(TABLES / "invalidations-and-exclusions.csv", invalidation_rows())
    write_csv(TABLES / "carrier-comparison.csv", carrier)
    write_csv(TABLES / "model-reasoning-matrix.csv", matrix)
    write_csv(TABLES / "experiment-2-effort.csv", effort2)
    write_csv(PROVENANCE / "frozen-tags.csv", frozen_tag_rows())
    write_csv(PROVENANCE / "runtime-images.csv", runtime_image_rows())
    bar_chart(
        FIGURES / "figure-2-equal-bag-ab.svg",
        "Experiment 2: equal-word-bag paired discrimination",
        ["signal N=2", "signal N=4", "all-shuffled target answers"],
        [19 / 40, 8 / 40, 0 / 80],
        ["19/40 pairs", "8/40 pairs", "0/80 trials"],
        ["#2563eb", "#60a5fa", "#dc2626"],
        [wilson(19, 40), wilson(8, 40), wilson(0, 80)],
    )
    figure_1()
    figure_1b()
    figure_3(carrier)
    figure_4(matrix)
    figure_5(effort2)
    sources = [
        REPO / "experiment-2/results/answer-identity.csv",
        REPO / "experiment-2/results/paired-discrimination.csv",
        REPO / "experiment-2/results/effort-summary.csv",
        REPO / "experiment-3/results/model-reasoning-matrix.csv",
        REPO / "experiment-4/uniform/results/carrier-comparison.csv",
        REPO / "experiment-4/uniform/results/effort-summary.csv",
        REPO / "experiment-6/five-symbol-v2/results/clean-gate.json",
        REPO / "experiment-6/five-symbol-v2/results/scrambled-gate.json",
    ]
    summary = {
        "schema_version": 1,
        "source_data_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "central_claim": "behavioral sensitivity to embedded linguistic order under lexically matched interference",
        "experiment_4a_geometry": {"signal_words": 161, "distractor_words": 161, "total_positions": 322, "density": 0.5},
        "core_metrics": core,
        "experiment_6_stop": "clean task passed 40/40; scrambled control produced 2/10 targets; no buried-signal prompts generated",
        "source_sha256": {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
    }
    (PAPER / "publication-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"tables": 6, "figures": 6, "provenance_manifests": 2, "core_metrics": len(core)}, indent=2))


if __name__ == "__main__":
    main()
