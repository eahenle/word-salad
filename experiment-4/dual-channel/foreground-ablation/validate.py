#!/usr/bin/env python3
"""Fail-closed invariants for Experiment 4C.1."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from generate_decohered import CONDITIONS, FRAME, ROOT, SOURCE_ROOT, TOPICS, build


SOURCE_COMMIT = "d5dc2a837086a06b85361130c7e56ea957c9a650"
SOURCE_TAG = "experiment-4c-dual-channel-negative-gate"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def simulate(words: list[str]) -> str:
    prefix = ["Rowan", "Mira", "Tavi", "are", "initially", "ordered"]
    suffix = ["output", "the", "central", "name"]
    if words[:6] != prefix or words[-4:] != suffix:
        raise ValueError("invalid frozen task frame")
    middle = words[6:-4]; divider = middle.index("afterward")
    state = prefix[:3]
    for operation in (middle[:divider], middle[divider + 1:]):
        if operation[0] == "exchange":
            left, right = operation[1], operation[3]
            i, j = state.index(left), state.index(right); state[i], state[j] = state[j], state[i]
        elif operation[0] == "relocate":
            item, reference = operation[1], operation[3]
            state.remove(item); state.insert(state.index(reference) + 1, item)
        else:
            raise ValueError(f"unknown operation {operation}")
    return state[1]


def validate() -> dict:
    source_freeze = json.loads((SOURCE_ROOT / "results/experiment-freeze.json").read_text())
    records = build(); failures = []; rows = []
    if source_freeze["model"] != "gpt-5.6-sol" or source_freeze["reasoning"] != "medium":
        failures.append("frozen subject configuration changed")
    if source_freeze["frame"] != FRAME:
        failures.append("prompt frame changed")
    if source_freeze["answer_key"] != {"A": "Rowan", "B": "Mira"}:
        failures.append("frozen answer key changed")
    source_hashes = source_freeze["document_hashes"]
    for record in records:
        source_id = record["source_trial_id"]; original = record["source_document"].split()
        output = record["document"].split(); positions = record["signal_positions"]
        source_metadata_path = SOURCE_ROOT / "development/metadata" / f"{source_id}.json"
        source_metadata = json.loads(source_metadata_path.read_text())
        extracted_original = [original[index] for index in positions]
        extracted_output = [output[index] for index in positions]
        checks = {
            "source_document_hash_matches_4c_freeze": record["source_document_sha256"] == source_hashes[source_id],
            "word_count_preserved": len(original) == len(output) == record["document_words"],
            "full_document_bag_preserved": Counter(original) == Counter(output),
            "signal_positions_unchanged": positions == source_metadata["signal_positions"],
            "signal_words_unchanged": extracted_original == extracted_output == source_metadata["signal_tokens"],
            "noise_destination_count": len(record["noise_destination_indices"]) == len(original) - 19,
            "noise_source_indices_form_permutation": sorted(record["noise_source_indices_by_destination"]) == record["noise_destination_indices"],
            "noise_permutation_changed": record["noise_permutation_changed"],
            "prompt_frame_exact": (ROOT / "development/prompts" / f"{record['trial_id']}.txt").read_text() == FRAME + "\n\n" + record["document"],
        }
        if record["condition"] in {"hidden_a", "hidden_b"}:
            identity = record["hidden_identity"]
            checks["answer_key_resimulated"] = simulate(extracted_output) == source_freeze["answer_key"][identity]
        else:
            checks["scrambled_stream_not_intact"] = extracted_output not in [source_freeze["payloads"][key].split() for key in ("A", "B")]
            checks["scrambled_stream_bag_matches_payload"] = Counter(extracted_output) == Counter(source_freeze["payloads"]["A"].split())
        for name, passed in checks.items():
            if not passed:
                failures.append(f"{record['trial_id']}: {name}")
        rows.append({
            "trial_id": record["trial_id"], "source_trial_id": source_id,
            "topic": record["topic"], "condition": record["condition"],
            "document_words": len(output), "signal_words": len(positions),
            "signal_density": record["signal_density"], "noise_fixed_points": record["noise_fixed_points"],
            "source_document_sha256": record["source_document_sha256"],
            "document_sha256": record["document_sha256"], "prompt_sha256": record["prompt_sha256"],
            "checks": checks,
        })
    report = {
        "passed": not failures, "failures": failures,
        "source_commit": SOURCE_COMMIT, "source_tag": SOURCE_TAG,
        "source_experiment_gate": json.loads((SOURCE_ROOT / "results/development-gate.json").read_text()),
        "frame_exactly_reused": FRAME, "scheduled_trials": 9,
        "topics": list(TOPICS), "conditions": list(CONDITIONS), "records": rows,
    }
    if failures:
        raise AssertionError("\n".join(failures))
    return report


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))

