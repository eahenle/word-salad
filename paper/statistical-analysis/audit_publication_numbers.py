#!/usr/bin/env python3
"""Fail-closed audit of publication-facing counts against frozen results."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path


PAPER = Path(__file__).resolve().parents[1]
REPO = PAPER.parent
REPORT = PAPER / "provenance" / "publication-number-audit.json"
FREEZE = PAPER / "provenance" / "evidence-freeze.json"


def csv_rows(relative: str) -> list[dict[str, str]]:
    with (REPO / relative).open(newline="") as stream:
        return list(csv.DictReader(stream))


def json_value(relative: str):
    return json.loads((REPO / relative).read_text())


def jsonl_rows(relative: str) -> list[dict]:
    return [json.loads(line) for line in (REPO / relative).read_text().splitlines() if line]


def integer(row: dict, key: str) -> int:
    return int(row[key])


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Audit:
    def __init__(self) -> None:
        self.checks: list[dict] = []
        self.failures: list[str] = []

    def equal(self, name: str, observed, expected, source: str) -> None:
        passed = observed == expected
        self.checks.append(
            {
                "name": name,
                "passed": passed,
                "observed": observed,
                "expected": expected,
                "source": source,
            }
        )
        if not passed:
            self.failures.append(f"{name}: observed {observed!r}, expected {expected!r}")

    def true(self, name: str, observed: bool, source: str) -> None:
        self.equal(name, bool(observed), True, source)


def experiment_1c(audit: Audit) -> None:
    summary_path = "experiment-1c/results/summary.csv"
    rows = csv_rows(summary_path)
    variants = ["original", "lower", "nopunct", "lower_nopunct"]
    audit.equal("1C normalization variants", sorted({r["variant"] for r in rows}), sorted(variants), summary_path)
    audit.equal("1C scheduled trials", sum(integer(r, "trials") for r in rows), 320, summary_path)
    signal = {variant: sum(integer(r, "semantic_success") for r in rows if r["variant"] == variant and r["condition"] == "signal") for variant in variants}
    shuffled = {variant: sum(integer(r, "semantic_success") for r in rows if r["variant"] == variant and r["condition"] == "all_shuffled") for variant in variants}
    audit.equal("1C signal semantic successes by variant", signal, {"original": 22, "lower": 18, "nopunct": 22, "lower_nopunct": 18}, summary_path)
    audit.equal("1C shuffled semantic successes by variant", shuffled, {"original": 0, "lower": 1, "nopunct": 1, "lower_nopunct": 0}, summary_path)

    effort_path = "experiment-1c/results/effort-rollup.csv"
    effort = csv_rows(effort_path)
    totals = {
        condition: {
            "timeouts": sum(integer(r, "timeouts") for r in effort if r["condition"] == condition),
            "trials_with_tools": sum(integer(r, "trials_with_tools") for r in effort if r["condition"] == condition),
        }
        for condition in ("signal", "all_shuffled")
    }
    audit.equal("1C timeout/tool totals", totals, {"signal": {"timeouts": 11, "trials_with_tools": 45}, "all_shuffled": {"timeouts": 30, "trials_with_tools": 100}}, effort_path)


def experiment_2(audit: Audit) -> None:
    identity_path = "experiment-2/results/answer-identity.csv"
    rows = csv_rows(identity_path)
    signal = defaultdict(int)
    for row in rows:
        if row["condition"] == "signal":
            signal[int(row["lanes"])] += integer(row, "expected_success")
    audit.equal("Experiment 2 expected individuals", dict(signal), {2: 57, 4: 33}, identity_path)
    clean = sum(integer(r, "expected_success") for r in rows if r["condition"] == "clean")
    audit.equal("Experiment 2 clean baseline", clean, 80, identity_path)
    shuffled_trials = sum(integer(r, "trials") for r in rows if r["condition"] == "all_shuffled")
    shuffled_targets = sum(integer(r, "answer_A") + integer(r, "answer_B") for r in rows if r["condition"] == "all_shuffled")
    audit.equal("Experiment 2 shuffled trials", shuffled_trials, 80, identity_path)
    audit.equal("Experiment 2 shuffled target answers", shuffled_targets, 0, identity_path)

    pairs_path = "experiment-2/results/paired-discrimination.csv"
    pairs = csv_rows(pairs_path)
    paired = {lanes: sum(integer(r, "both_expected") for r in pairs if r["condition"] == "signal" and int(r["lanes"]) == lanes) for lanes in (2, 4)}
    pair_denominators = {lanes: sum(integer(r, "paired_seeds") for r in pairs if r["condition"] == "signal" and int(r["lanes"]) == lanes) for lanes in (2, 4)}
    audit.equal("Experiment 2 complete A/B pairs", paired, {2: 19, 4: 8}, pairs_path)
    audit.equal("Experiment 2 A/B pair denominators", pair_denominators, {2: 40, 4: 40}, pairs_path)

    raw_cells_path = "experiment-2/results/raw-model-pilot-cells.csv"
    raw_cells = csv_rows(raw_cells_path)
    tool_less_signal = sum(integer(r, "semantic_success") for r in raw_cells if r["regime"] == "tool_less" and r["condition"] == "signal" and r["lanes"] == "2")
    tool_less_signal_trials = sum(integer(r, "scheduled") for r in raw_cells if r["regime"] == "tool_less" and r["condition"] == "signal" and r["lanes"] == "2")
    tool_less_control_targets = sum(integer(r, "target_answers") for r in raw_cells if r["regime"] == "tool_less" and r["condition"] == "all_shuffled")
    audit.equal("Tool-less N=2 expected individuals", [tool_less_signal, tool_less_signal_trials], [35, 40], raw_cells_path)
    audit.equal("Tool-less shuffled target answers", tool_less_control_targets, 0, raw_cells_path)
    raw_pairs_path = "experiment-2/results/raw-model-pilot-pairs.csv"
    raw_pairs = csv_rows(raw_pairs_path)
    tool_less_pair = next(r for r in raw_pairs if r["regime"] == "tool_less")
    audit.equal("Tool-less complete A/B pairs", [integer(tool_less_pair, "A_to_A_and_B_to_B"), integer(tool_less_pair, "pairs")], [16, 20], raw_pairs_path)


def experiment_3(audit: Audit) -> None:
    matrix_path = "experiment-3/results/model-reasoning-matrix.csv"
    rows = csv_rows(matrix_path)
    totals = {
        "fixed_individual": sum(integer(r, "fixed_individual") for r in rows),
        "fixed_individual_trials": sum(integer(r, "fixed_individual_trials") for r in rows),
        "fixed_paired": sum(integer(r, "fixed_paired") for r in rows),
        "fixed_pairs": sum(integer(r, "fixed_pairs") for r in rows),
        "jitter_individual": sum(integer(r, "jitter_individual") for r in rows),
        "jitter_individual_trials": sum(integer(r, "jitter_individual_trials") for r in rows),
        "jitter_paired": sum(integer(r, "jitter_paired") for r in rows),
        "jitter_pairs": sum(integer(r, "jitter_pairs") for r in rows),
        "control_target_answers": sum(integer(r, "control_target_answers") for r in rows),
    }
    audit.equal("Experiment 3 screening totals", totals, {"fixed_individual": 69, "fixed_individual_trials": 240, "fixed_paired": 17, "fixed_pairs": 120, "jitter_individual": 95, "jitter_individual_trials": 240, "jitter_paired": 31, "jitter_pairs": 120, "control_target_answers": 0}, matrix_path)

    spark = [r for r in rows if r["model"] == "gpt-5.3-codex-spark"]
    spark_totals = {
        "fixed_individual": sum(integer(r, "fixed_individual") for r in spark),
        "jitter_individual": sum(integer(r, "jitter_individual") for r in spark),
        "fixed_paired": sum(integer(r, "fixed_paired") for r in spark),
        "jitter_paired": sum(integer(r, "jitter_paired") for r in spark),
    }
    audit.equal("Experiment 3 Spark screening boundary", spark_totals, {"fixed_individual": 0, "jitter_individual": 1, "fixed_paired": 0, "jitter_paired": 0}, matrix_path)

    confirmation_path = "experiment-3/results/confirmation-summary.csv"
    confirmation = csv_rows(confirmation_path)
    selected = {}
    for row in confirmation:
        if row["cohort"] == "confirmation":
            selected[f"{row['model']}:{row['reasoning']}:{row['carrier']}"] = [integer(row, "individual_success"), integer(row, "individual_trials"), integer(row, "paired_success"), integer(row, "pairs")]
    audit.equal(
        "Experiment 3 selected-cell confirmation",
        selected,
        {
            "gpt-5.6-sol:medium:fixed": [14, 20, 6, 10],
            "gpt-5.6-sol:medium:jitter": [14, 20, 6, 10],
            "gpt-5.6-terra:xhigh:fixed": [7, 20, 2, 10],
            "gpt-5.6-terra:xhigh:jitter": [9, 20, 3, 10],
            "gpt-5.3-codex-spark:xhigh:fixed": [0, 20, 0, 10],
            "gpt-5.3-codex-spark:xhigh:jitter": [0, 20, 0, 10],
        },
        confirmation_path,
    )

    identity_path = "experiment-3/results/answer-identity.csv"
    identity = csv_rows(identity_path)
    controls = [r for r in identity if r["carrier"] == "all-shuffled"]
    audit.equal("Experiment 3 shuffled controls", sum(integer(r, "trials") for r in controls), 36, identity_path)
    audit.equal("Experiment 3 shuffled target answers", sum(integer(r, "answer_A") + integer(r, "answer_B") for r in controls), 0, identity_path)


def experiment_4a(audit: Audit) -> None:
    validation_path = "experiment-4/uniform/results/prompt-validation.json"
    validation = json_value(validation_path)
    geometry = {key: validation[key] for key in ("frozen_payload_word_count", "total_positions", "signal_positions", "distractor_positions")}
    audit.equal("Experiment 4A geometry", geometry, {"frozen_payload_word_count": 161, "total_positions": 322, "signal_positions": 161, "distractor_positions": 161}, validation_path)
    audit.true("Experiment 4A uniform sample without replacement", validation["uniform_sample_without_replacement"], validation_path)

    carrier_path = "experiment-4/uniform/results/carrier-comparison.csv"
    carrier = csv_rows(carrier_path)
    uniform = {f"{r['model']}:{r['reasoning']}": [integer(r, "individual_success"), integer(r, "individual_trials"), integer(r, "paired_success"), integer(r, "pairs")] for r in carrier if r["carrier"] == "uniform"}
    audit.equal("Experiment 4A per-cell outcomes", uniform, {"gpt-5.6-sol:medium": [30, 40, 13, 20], "gpt-5.6-terra:xhigh": [16, 40, 5, 20]}, carrier_path)
    aggregate = [sum(v[index] for v in uniform.values()) for index in range(4)]
    audit.equal("Experiment 4A aggregate outcomes", aggregate, [46, 80, 18, 40], carrier_path)

    effort_path = "experiment-4/uniform/results/effort-summary.csv"
    effort = csv_rows(effort_path)
    controls = [r for r in effort if r["condition"] == "all_shuffled"]
    audit.equal("Experiment 4A shuffled controls", [sum(integer(r, "trials") for r in controls), sum(integer(r, "target_answers") for r in controls)], [10, 0], effort_path)
    audit.equal("Experiment 4A completed subjects", sum(integer(r, "trials") for r in effort), 90, effort_path)
    audit.equal("Experiment 4A timeouts", sum(integer(r, "timeouts") for r in effort), 0, effort_path)


def experiments_5_6(audit: Audit) -> None:
    cloud_path = "experiment-5/cloud-context-audit/results/unblinding-audit.json"
    cloud = json_value(cloud_path)
    audit.equal("Cloud-history exact recovery", cloud["cloud_exact_recoveries"], 0, cloud_path)
    audit.equal("Cloud-history probes", len(cloud["expected_value_sha256_by_trial"]), 5, cloud_path)
    audit.equal("Cloud negative controls UNKNOWN", cloud["negative_controls_returning_unknown"], 5, cloud_path)

    v1_path = "experiment-6/five-symbol/results/clean-gate.json"
    v1 = json_value(v1_path)
    audit.equal("Experiment 6 v1 clean exact", [v1["aggregate_normalized_exact"], v1["aggregate_trials"]], [0, 40], v1_path)
    v2_path = "experiment-6/five-symbol-v2/results/clean-gate.json"
    v2 = json_value(v2_path)
    audit.equal("Experiment 6 v2 clean exact", [v2["aggregate_normalized_exact"], v2["aggregate_trials"]], [40, 40], v2_path)
    scrambled_path = "experiment-6/five-symbol-v2/results/scrambled-gate.json"
    scrambled = json_value(scrambled_path)
    audit.equal("Experiment 6 v2 shuffled target A count", [scrambled["target_sequence_selections"], scrambled["controls"]], [2, 10], scrambled_path)
    audit.equal("Experiment 6 v2 buried-signal authorization", scrambled["advance_buried_signal_authorized"], False, scrambled_path)
    cohort_dirs = sorted(path.name for path in (REPO / "experiment-6/five-symbol-v2/cohorts").iterdir() if path.is_dir())
    audit.equal("Experiment 6 v2 executed cohort directories", cohort_dirs, ["clean", "scrambled"], "experiment-6/five-symbol-v2/cohorts/")


def publication_layer(audit: Audit) -> None:
    markdown = "\n".join(path.read_text() for path in sorted(PAPER.rglob("*.md")))
    audit.true("No stale legacy signal count in publication markdown", re.search(r"\b196\b", markdown) is None, "paper/**/*.md")
    audit.true("No stale legacy total count in publication markdown", re.search(r"\b392\b", markdown) is None, "paper/**/*.md")
    audit.true("No overstrong Experiment 6 order-independent wording", "order-independent" not in markdown.lower(), "paper/**/*.md")
    audit.true("Correct Experiment 4A exact geometry appears", "161-of-322" in markdown and "161 signal and 161 distractor words in 322 positions" in markdown, "paper/**/*.md")

    required = {
        "paper/claims-and-evidence.md": ["57/80", "33/80", "19/40", "8/40", "0/80", "30/40", "13/20", "16/40", "5/20", "46/80", "18/40", "0/10", "40/40", "2/10"],
        "paper/publication-readiness.md": ["161-of-322", "18/40", "46/80", "0/10", "0/40", "40/40", "2/10"],
    }
    for relative, fragments in required.items():
        text = (REPO / relative).read_text()
        audit.equal(f"Canonical numeric fragments in {relative}", [fragment for fragment in fragments if fragment not in text], [], relative)

    generated_core = csv_rows("paper/results-tables/core-evidence.csv")
    expected_core = {
        "Experiment 2 | N=2 expected individuals": [57, 80],
        "Experiment 2 | N=2 complete A/B pairs": [19, 40],
        "Experiment 2 | N=4 expected individuals": [33, 80],
        "Experiment 2 | N=4 complete A/B pairs": [8, 40],
        "Experiment 2 | all-shuffled target answers": [0, 80],
        "Experiment 2 tool-less pilot | N=2 expected individuals": [35, 40],
        "Experiment 2 tool-less pilot | N=2 complete A/B pairs": [16, 20],
        "Experiment 3 | fixed expected individuals": [69, 240],
        "Experiment 3 | fixed complete A/B pairs": [17, 120],
        "Experiment 3 | jitter expected individuals": [95, 240],
        "Experiment 3 | jitter complete A/B pairs": [31, 120],
        "Experiment 4A | uniform expected individuals": [46, 80],
        "Experiment 4A | uniform complete A/B pairs": [18, 40],
        "Experiment 4A | all-shuffled target answers": [0, 10],
        "Experiment 6 v2 | clean exact execution": [40, 40],
        "Experiment 6 v2 | scrambled target false positives": [2, 10],
    }
    observed_core = {f"{r['study']} | {r['endpoint']}": [integer(r, "successes"), integer(r, "trials")] for r in generated_core}
    audit.equal("Generated core-evidence table", observed_core, expected_core, "paper/results-tables/core-evidence.csv")
    audit.equal("Generated carrier comparison is frozen source", file_sha256(REPO / "paper/results-tables/carrier-comparison.csv"), file_sha256(REPO / "experiment-4/uniform/results/carrier-comparison.csv"), "paper/results-tables/carrier-comparison.csv")
    audit.equal("Generated model matrix is frozen source", file_sha256(REPO / "paper/results-tables/model-reasoning-matrix.csv"), file_sha256(REPO / "experiment-3/results/model-reasoning-matrix.csv"), "paper/results-tables/model-reasoning-matrix.csv")


def write_evidence_freeze() -> None:
    artifacts = []
    explicit = [
        PAPER / "claims-and-evidence.md",
        PAPER / "manuscript-outline.md",
        PAPER / "methods.md",
        PAPER / "publication-readiness.md",
        PAPER / "publication-summary.json",
        PAPER / "statistical-analysis/build_paper.py",
        PAPER / "statistical-analysis/audit_publication_numbers.py",
        REPORT,
    ]
    explicit.extend(sorted((PAPER / "results-tables").glob("*.csv")))
    explicit.extend(sorted((PAPER / "figures").glob("*.svg")))
    for path in explicit:
        artifacts.append({"path": str(path.relative_to(REPO)), "sha256": file_sha256(path), "bytes": path.stat().st_size})
    data = {
        "schema_version": 1,
        "status": "evidence_layer_frozen_before_polished_manuscript",
        "expected_tag": "paper-evidence-freeze-v1",
        "base_commit_before_evidence_freeze": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "artifacts": artifacts,
    }
    FREEZE.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-manifest", action="store_true")
    args = parser.parse_args()
    audit = Audit()
    experiment_1c(audit)
    experiment_2(audit)
    experiment_3(audit)
    experiment_4a(audit)
    experiments_5_6(audit)
    publication_layer(audit)
    report = {
        "schema_version": 1,
        "status": "pass" if not audit.failures else "fail",
        "checks_passed": sum(check["passed"] for check in audit.checks),
        "checks_total": len(audit.checks),
        "failures": audit.failures,
        "checks": audit.checks,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    if audit.failures:
        raise SystemExit("publication-number audit FAILED:\n- " + "\n- ".join(audit.failures))
    if args.freeze_manifest:
        write_evidence_freeze()
    print(json.dumps({"status": "pass", "checks": len(audit.checks), "freeze_manifest_written": args.freeze_manifest}, indent=2))


if __name__ == "__main__":
    main()
