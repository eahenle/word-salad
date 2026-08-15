#!/usr/bin/env python3
"""Scan active frozen subject traces for observable task-family awareness."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PATTERN = re.compile(
    r"\b(?:hidden|embedded|interleav(?:e|ed|ing)|stride|every[ -]other|"
    r"word[- ]order(?:ing)?|reconstruct(?:s|ed|ing|ion)?|decod(?:e|ed|er|ing)|"
    r"encod(?:e|ed|ing)|signals?|noises?|shuffl(?:e|ed|ing)|"
    r"scrambl(?:e|ed|ing))\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Cohort:
    name: str
    experiment: str
    root: Path
    trace_root: Path
    results: Path
    surface: str
    visible_assessment: str
    prompt_base: Path


COHORTS = (
    Cohort("experiment_1b", "1B", REPO / "experiment-1b", REPO / "experiment-1b/traces",
           REPO / "experiment-1b/results/trials.jsonl", "visibly_multiplexed_word_salad",
           "directly_suggested_by_visible_structure", REPO / "experiment-1b"),
    Cohort("experiment_1c", "1C", REPO / "experiment-1c", REPO / "experiment-1c/traces",
           REPO / "experiment-1c/results/trials.jsonl", "visibly_multiplexed_word_salad",
           "directly_suggested_by_visible_structure", REPO / "experiment-1c"),
    Cohort("experiment_2", "2", REPO / "experiment-2", REPO / "experiment-2/traces",
           REPO / "experiment-2/results/trials.jsonl", "visibly_multiplexed_word_salad",
           "directly_suggested_by_visible_structure", REPO / "experiment-2"),
    Cohort("experiment_3", "3", REPO / "experiment-3", REPO / "experiment-3/traces",
           REPO / "experiment-3/results/trials.jsonl", "visibly_multiplexed_word_salad",
           "directly_suggested_by_visible_structure", REPO / "experiment-3"),
    Cohort("experiment_4a", "4A", REPO / "experiment-4/uniform",
           REPO / "experiment-4/uniform/traces", REPO / "experiment-4/uniform/results/trials.jsonl",
           "visibly_multiplexed_word_salad", "directly_suggested_by_visible_structure",
           REPO / "experiment-4"),
    Cohort("experiment_4b_defensive", "4B", REPO / "experiment-4/stego-poc",
           REPO / "experiment-4/stego-poc/development/traces",
           REPO / "experiment-4/stego-poc/development/results/trials.jsonl",
           "natural_evaluation_like_with_defensive_frame",
           "visible_marker_and_summary_language_is_a_strong_local_confound",
           REPO / "experiment-4/stego-poc"),
    Cohort("experiment_4b1_raw", "4B.1", REPO / "experiment-4/stego-poc/framing-ablation",
           REPO / "experiment-4/stego-poc/framing-ablation/development/raw/traces",
           REPO / "experiment-4/stego-poc/framing-ablation/development/raw/results/trials.jsonl",
           "natural_evaluation_like_raw_text",
           "not_visibly_scrambled_but_marker_color_record_and_summary_language_is_visible",
           REPO / "experiment-4/stego-poc/framing-ablation"),
    Cohort("experiment_4c", "4C", REPO / "experiment-4/dual-channel",
           REPO / "experiment-4/dual-channel/development/traces",
           REPO / "experiment-4/dual-channel/results/trials.jsonl",
           "ordinary_coherent_natural_prose", "not_suggested_by_visible_structure",
           REPO / "experiment-4/dual-channel"),
    Cohort("experiment_4c1", "4C.1", REPO / "experiment-4/dual-channel/foreground-ablation",
           REPO / "experiment-4/dual-channel/foreground-ablation/development/traces",
           REPO / "experiment-4/dual-channel/foreground-ablation/results/trials.jsonl",
           "visibly_decohered_same_topic_foreground",
           "directly_suggested_by_visible_structure",
           REPO / "experiment-4/dual-channel/foreground-ablation"),
    Cohort("experiment_4c2_d125", "4C.2-d125", REPO / "experiment-4/dual-channel/density-ladder",
           REPO / "experiment-4/dual-channel/density-ladder/development/d125/traces",
           REPO / "experiment-4/dual-channel/density-ladder/development/d125/results/trials.jsonl",
           "visibly_decohered_same_topic_foreground",
           "directly_suggested_by_visible_structure",
           REPO / "experiment-4/dual-channel/density-ladder"),
    Cohort("local_context_probes", "local-context-probes", REPO / "experiment-4/context-audit",
           REPO / "experiment-4/context-audit/behavioral-probes/traces",
           REPO / "experiment-4/context-audit/behavioral-probes/results.jsonl",
           "ordinary_unrelated_benign_prose", "not_suggested_by_visible_structure",
           REPO / "experiment-4/context-audit"),
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(errors="replace").splitlines() if line.strip()]


def config_slug(record: dict) -> str:
    return f"{str(record.get('model', '')).replace('.', '_')}__{record.get('reasoning', '')}"


def record_index(cohort: Cohort) -> dict[tuple[str, str | None], dict]:
    rows = read_jsonl(cohort.results)
    if cohort.name == "experiment_3":
        rows.extend(read_jsonl(REPO / "experiment-3/results/confirmation-trials.jsonl"))
    index = {}
    for row in rows:
        trial_id = str(row.get("trial_id") or row.get("neutral_id") or row.get("probe_id"))
        config = config_slug(row) if cohort.name in {"experiment_3", "experiment_4a"} else None
        key = (trial_id, config)
        if key in index:
            raise RuntimeError(f"duplicate result key for {cohort.name}: {key}")
        index[key] = row
    return index


def trace_paths(cohort: Cohort) -> list[Path]:
    return sorted(cohort.trace_root.rglob("*.jsonl"))


def prompt_path(cohort: Cohort, record: dict, trial_id: str) -> Path:
    for key in ("prompt_file", "prompt_origin"):
        relative = record.get(key)
        if relative:
            candidate = (cohort.prompt_base / str(relative)).resolve()
            if candidate.exists():
                return candidate
    candidates = [
        path for path in cohort.root.rglob(f"{trial_id}.txt")
        if "prompts" in path.parts or "documents" in path.parts
    ]
    if cohort.name == "experiment_4b1_raw":
        external = REPO / "experiment-4/stego-poc/development/documents" / f"{trial_id}.txt"
        if external.exists():
            return external
    prompt_candidates = [path for path in candidates if "prompts" in path.parts]
    if len(prompt_candidates) == 1:
        return prompt_candidates[0]
    if len(candidates) != 1:
        raise RuntimeError(f"could not uniquely resolve prompt for {cohort.name}/{trial_id}: {candidates}")
    return candidates[0]


def observable_fields(path: Path) -> list[tuple[int, str, str]]:
    fields = []
    for line_number, raw in enumerate(path.read_text(errors="replace").splitlines(), 1):
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        item_type = str(item.get("type", "unknown"))
        if item_type == "agent_message":
            fields.append((line_number, "agent_message", str(item.get("text", ""))))
        elif item_type == "reasoning":
            for key in ("text", "summary"):
                if isinstance(item.get(key), str):
                    fields.append((line_number, f"reasoning_{key}", item[key]))
        elif item_type == "command_execution":
            fields.append((line_number, "shell_command", str(item.get("command", ""))))
            fields.append((line_number, "shell_output", str(item.get("aggregated_output", ""))))
        elif item_type == "web_search":
            fields.append((line_number, "web_search", json.dumps(item, ensure_ascii=False)))
    return fields


def excerpt(text: str, start: int, end: int, radius: int = 100) -> str:
    clean = re.sub(r"\s+", " ", text)
    # Match offsets refer to the original text, so locate the exact matched token again near a
    # bounded original slice rather than pretending normalized offsets are identical.
    raw = text[max(0, start - radius):min(len(text), end + radius)]
    return re.sub(r"\s+", " ", raw).strip()


def metadata_for(cohort: Cohort, record: dict) -> dict | None:
    trial_id = str(record.get("trial_id") or record.get("neutral_id") or record.get("probe_id"))
    candidates = []
    if cohort.name in {"experiment_4b_defensive", "experiment_4b1_raw"}:
        candidates.append(REPO / "experiment-4/stego-poc/development/metadata" / f"{trial_id}.json")
    elif cohort.name in {"experiment_4c", "experiment_4c1"}:
        candidates.append(cohort.root / "development/metadata" / f"{trial_id}.json")
    elif cohort.name == "experiment_4c2_d125":
        candidates.append(cohort.root / "development/d125/metadata" / f"{trial_id}.json")
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text())
    return None


def density(cohort: Cohort, record: dict) -> float | None:
    condition = str(record.get("condition", "")).lower()
    if condition in {"all_shuffled", "all-shuffled", "cover_only", "benign"}:
        return 0.0
    metadata = metadata_for(cohort, record)
    if metadata:
        if isinstance(metadata.get("signal_density"), (int, float)):
            return round(float(metadata["signal_density"]), 6)
        configuration = metadata.get("configuration")
        if isinstance(configuration, dict) and isinstance(configuration.get("density"), (int, float)):
            return round(float(configuration["density"]), 6)
        total = metadata.get("document_words") or metadata.get("document_word_count")
        positions = metadata.get("signal_positions")
        if isinstance(total, int) and total > 0 and isinstance(positions, list):
            return round(len(positions) / total, 6)
    lanes = record.get("lanes")
    if isinstance(lanes, int) and lanes > 0:
        if condition == "clean":
            return 1.0
        if condition == "signal":
            return 1.0 / lanes
    if cohort.name == "experiment_4a" and condition == "signal":
        return 0.5
    return None


def framing_mentions_structure(cohort: Cohort) -> bool:
    # Subject-level instructions never disclosed hidden channels. The 4C frame asks only for
    # "the answer implied by" the text, which does not name a structural mechanism.
    return False


def scan() -> tuple[list[dict], list[dict], dict]:
    occurrences = []
    timelines = []
    cohort_counts = {}
    global_terms = Counter()
    for cohort in COHORTS:
        index = record_index(cohort)
        traces = trace_paths(cohort)
        hit_trials = 0
        occurrence_count = 0
        cohort_terms = Counter()
        for trace in traces:
            trial_id = trace.stem
            config = trace.parent.name if cohort.name in {"experiment_3", "experiment_4a"} else None
            record = index.get((trial_id, config))
            if record is None:
                raise RuntimeError(f"missing result record for {cohort.name}/{trial_id}/{config}")
            prompt = prompt_path(cohort, record, trial_id)
            prompt_text = prompt.read_text(errors="replace")
            expected_hash = record.get("prompt_sha256")
            actual_hash = hashlib.sha256(prompt.read_bytes()).hexdigest()
            trace_hash = hashlib.sha256(trace.read_bytes()).hexdigest()
            if expected_hash and expected_hash != actual_hash:
                raise RuntimeError(f"prompt hash mismatch for {cohort.name}/{trial_id}")
            trial_occurrences = []
            for line_number, field, text in observable_fields(trace):
                for match in PATTERN.finditer(text):
                    term = match.group(0).lower()
                    cohort_terms[term] += 1
                    global_terms[term] += 1
                    trial_occurrences.append({
                        "experiment": cohort.experiment,
                        "cohort": cohort.name,
                        "trial_id": trial_id,
                        "condition": record.get("condition") or record.get("arm"),
                        "carrier": record.get("carrier"),
                        "variant": record.get("variant"),
                        "model": record.get("model"),
                        "reasoning": record.get("reasoning"),
                        "signal_density": density(cohort, record),
                        "started_at": (record.get("runner") or {}).get("started_at") or record.get("started_at"),
                        "surface_class": cohort.surface,
                        "visible_stimulus_assessment": cohort.visible_assessment,
                        "experimenter_framing_named_structure": framing_mentions_structure(cohort),
                        "trace_file": str(trace.relative_to(REPO)),
                        "trace_sha256": trace_hash,
                        "trace_line": line_number,
                        "observable_field": field,
                        "matched_term": term,
                        "evidence_excerpt": excerpt(text, match.start(), match.end()),
                        "prompt_file": str(prompt.relative_to(REPO)),
                        "prompt_sha256": actual_hash,
                        "prompt_text": prompt_text,
                    })
            if trial_occurrences:
                hit_trials += 1
                occurrence_count += len(trial_occurrences)
                occurrences.extend(trial_occurrences)
                terms = Counter(row["matched_term"] for row in trial_occurrences)
                first = trial_occurrences[0]
                timelines.append({
                    "started_at": first["started_at"] or "",
                    "experiment": cohort.experiment,
                    "cohort": cohort.name,
                    "trial_id": trial_id,
                    "condition": first["condition"],
                    "carrier": first["carrier"],
                    "variant": first["variant"],
                    "model": first["model"],
                    "reasoning": first["reasoning"],
                    "signal_density": first["signal_density"],
                    "surface_class": cohort.surface,
                    "visible_stimulus_assessment": cohort.visible_assessment,
                    "experimenter_framing_named_structure": False,
                    "occurrence_count": len(trial_occurrences),
                    "matched_terms": "; ".join(f"{term}:{count}" for term, count in sorted(terms.items())),
                    "first_evidence_excerpt": first["evidence_excerpt"],
                    "prompt_file": first["prompt_file"],
                    "prompt_sha256": first["prompt_sha256"],
                    "trace_sha256": first["trace_sha256"],
                    "prompt_text": re.sub(r"\s+", " ", first["prompt_text"]).strip(),
                })
        cohort_counts[cohort.name] = {
            "experiment": cohort.experiment,
            "surface_class": cohort.surface,
            "traces_scanned": len(traces),
            "trials_with_awareness_terms": hit_trials,
            "observable_term_occurrences": occurrence_count,
            "term_counts": dict(sorted(cohort_terms.items())),
        }
    timelines.sort(key=lambda row: (row["started_at"], row["experiment"], row["trial_id"]))
    summary = {
        "schema_version": 1,
        "scope": "active frozen subject traces only; invalidated/smoke/isolation/capability traces excluded",
        "private_chain_of_thought_available": False,
        "traces_scanned": sum(row["traces_scanned"] for row in cohort_counts.values()),
        "trials_with_awareness_terms": len(timelines),
        "observable_term_occurrences": len(occurrences),
        "term_counts": dict(sorted(global_terms.items())),
        "cohorts": cohort_counts,
    }
    return occurrences, timelines, summary


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError("timeline unexpectedly empty")
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(stream.getvalue())


def main() -> None:
    occurrences, timelines, summary = scan()
    (ROOT / "awareness-occurrences.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in occurrences)
    )
    write_csv(ROOT / "awareness-timeline.csv", timelines)
    (ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({
        "traces_scanned": summary["traces_scanned"],
        "trials_with_awareness_terms": summary["trials_with_awareness_terms"],
        "observable_term_occurrences": summary["observable_term_occurrences"],
    }, indent=2))


if __name__ == "__main__":
    main()
