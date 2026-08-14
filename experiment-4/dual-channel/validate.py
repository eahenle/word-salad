#!/usr/bin/env python3
"""Fail-closed validation for Experiment 4C development stimuli."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from cover_generator import FRAME, TOPICS, build
from hidden_tasks import EXPECTED_ANSWERS, PAYLOADS, validate_payloads
from simulate import simulate, validate_answers


ROOT = Path(__file__).resolve().parent
PUNCTUATION = re.compile(r"[^\w]+", re.UNICODE)
FORBIDDEN_VISIBLE_FRAGMENTS = (
    "exchange rowan", "rowan and", "and tavi", "relocate mira",
    "mira beyond", "beyond rowan", "output the", "the central",
    "central name", "initially ordered", "ordered exchange",
    "ordered relocate", "give answer", "return rowan", "return mira",
    "choose rowan", "choose mira", "second token", "middle token",
)
PROHIBITED_COVER_TERMS = (
    "answer", "instruction", "instructions", "puzzle", "hidden", "encoded",
    "encoding", "decode", "decoding", "token", "tokens", "swap", "return",
)


def normalize_words(text: str) -> list[str]:
    output = []
    for word in text.split():
        normalized = PUNCTUATION.sub("", word).lower()
        if normalized:
            output.append(normalized)
    return output


def validate() -> dict:
    validate_payloads(); validate_answers()
    records = build(); failures: list[str] = []; report_records = []
    by_topic: dict[str, dict[str, dict]] = {}
    for record in records:
        trial_id = record["trial_id"]; document = record["document"]
        words = document.split(); positions = record["signal_positions"]
        extracted = [words[position] for position in positions]
        if extracted != record["signal_tokens"]:
            failures.append(f"{trial_id}: carrier extraction mismatch")
        gaps = [right - left for left, right in zip(positions, positions[1:])]
        if gaps and min(gaps) < 7:
            failures.append(f"{trial_id}: selected signals share a visible 2-6 word window")
        normalized = normalize_words(document)
        normalized_text = " ".join(normalized)
        fragment_hits = [fragment for fragment in FORBIDDEN_VISIBLE_FRAGMENTS
                         if fragment in normalized_text]
        term_hits = sorted({term for term in PROHIBITED_COVER_TERMS if term in normalized})
        if fragment_hits:
            failures.append(f"{trial_id}: forbidden local fragments {fragment_hits}")
        if term_hits:
            failures.append(f"{trial_id}: prohibited cover terms {term_hits}")
        if record["condition"].startswith("hidden_"):
            identity = record["hidden_identity"]
            if tuple(extracted) != PAYLOADS[identity]:
                failures.append(f"{trial_id}: wrong intact hidden identity")
            if simulate(tuple(extracted)) != EXPECTED_ANSWERS[identity]:
                failures.append(f"{trial_id}: simulated answer mismatch")
        elif record["condition"] == "scrambled":
            if Counter(extracted) != Counter(PAYLOADS["A"]):
                failures.append(f"{trial_id}: scrambled hidden bag mismatch")
            if tuple(extracted) in PAYLOADS.values():
                failures.append(f"{trial_id}: scrambled stream accidentally intact")
        elif positions or extracted:
            failures.append(f"{trial_id}: cover-only record has a selected carrier")
        prompt = FRAME + "\n\n" + document
        report_records.append({
            "trial_id": trial_id, "topic": record["topic"], "condition": record["condition"],
            "document_sha256": hashlib.sha256(document.encode()).hexdigest(),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "document_words": len(words), "prompt_words": len(prompt.split()),
            "signal_words": len(positions),
            "signal_density": round(len(positions) / len(words), 6) if words else 0,
            "minimum_signal_position_gap": min(gaps) if gaps else None,
            "forbidden_local_fragment_hits": fragment_hits,
            "prohibited_cover_term_hits": term_hits,
            "expected_answer": record["expected_answer"],
        })
        by_topic.setdefault(record["topic"], {})[record["condition"]] = record
    for topic, conditions in by_topic.items():
        required = {"hidden_a", "hidden_b", "scrambled", "cover_only"}
        if set(conditions) != required:
            failures.append(f"{topic}: wrong condition set")
            continue
        bags = [Counter(conditions[condition]["document"].split())
                for condition in ("hidden_a", "hidden_b", "scrambled")]
        if not bags[0] == bags[1] == bags[2]:
            failures.append(f"{topic}: A/B/scrambled full-document bags differ")
        if conditions["hidden_a"]["signal_positions"] == conditions["hidden_b"]["signal_positions"]:
            # Sentence order changes word offsets. Identical masks are neither required nor expected.
            failures.append(f"{topic}: carrier positions unexpectedly identical")
    prompt_hashes = [record["prompt_sha256"] for record in report_records]
    if len(prompt_hashes) != len(set(prompt_hashes)):
        failures.append("duplicate complete prompts")
    report = {
        "passed": not failures, "failures": failures,
        "frame": FRAME, "scheduled_trials": len(records),
        "topics": sorted(TOPICS), "conditions": ["hidden_a", "hidden_b", "scrambled", "cover_only"],
        "payload_word_count": len(PAYLOADS["A"]),
        "payload_bags_equal": Counter(PAYLOADS["A"]) == Counter(PAYLOADS["B"]),
        "simulated_answers": {identity: simulate(payload) for identity, payload in PAYLOADS.items()},
        "local_window_rule": {
            "visible_window_sizes": [2, 3, 4, 5, 6],
            "mechanical_requirement": "successive selected signal positions differ by at least 7 words",
            "consequence": "no visible 2-6 word window contains two selected signal words",
            "forbidden_fragment_count": len(FORBIDDEN_VISIBLE_FRAGMENTS),
        },
        "records": report_records,
    }
    if failures:
        raise AssertionError("\n".join(failures))
    return report


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, indent=2))

