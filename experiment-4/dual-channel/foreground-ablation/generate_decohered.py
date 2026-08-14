#!/usr/bin/env python3
"""Permute only frozen 4C nonsignal words while retaining every signal position."""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT.parent
FRAME = "Read the following text and give the answer implied by it."
TOPICS = ("ceramics", "garden", "harbor")
CONDITIONS = ("hidden_a", "hidden_b", "scrambled")
REPLICATE = 1
SEED_VERSION = "sha256-python-random-v1"


def seed_record(topic: str, condition: str, replicate: int = REPLICATE) -> dict:
    material = f"experiment-4c1\n{topic}\n{condition}\n{replicate}\n{SEED_VERSION}"
    digest = hashlib.sha256(material.encode()).hexdigest()
    return {"version": SEED_VERSION, "material": material, "sha256": digest,
            "integer": int(digest, 16)}


def build_one(topic: str, condition: str) -> dict:
    source_id = f"{topic}_{condition}"
    source_document_path = SOURCE_ROOT / "development/documents" / f"{source_id}.txt"
    source_metadata_path = SOURCE_ROOT / "development/metadata" / f"{source_id}.json"
    source_document = source_document_path.read_text(); source_metadata = json.loads(source_metadata_path.read_text())
    source_words = source_document.split(); positions = source_metadata["signal_positions"]
    position_set = set(positions)
    noise_entries = [(index, word) for index, word in enumerate(source_words) if index not in position_set]
    shuffled_entries = list(noise_entries); seed = seed_record(topic, condition)
    random.Random(seed["integer"]).shuffle(shuffled_entries)
    output_words = list(source_words); destinations = [index for index, _ in noise_entries]
    for destination, (_, word) in zip(destinations, shuffled_entries):
        output_words[destination] = word
    document = " ".join(output_words) + "\n"
    trial_id = f"{source_id}_decohered_r01"
    return {
        "trial_id": trial_id, "source_trial_id": source_id, "topic": topic,
        "condition": condition, "replicate": REPLICATE,
        "hidden_identity": source_metadata["hidden_identity"],
        "expected_answer": source_metadata["expected_answer"],
        "source_document": source_document, "document": document,
        "signal_positions": positions, "signal_tokens": source_metadata["signal_tokens"],
        "noise_source_indices_by_destination": [source_index for source_index, _ in shuffled_entries],
        "noise_destination_indices": destinations, "seed": seed,
        "source_document_sha256": hashlib.sha256(source_document.encode()).hexdigest(),
        "source_metadata_sha256": hashlib.sha256(source_metadata_path.read_bytes()).hexdigest(),
        "document_sha256": hashlib.sha256(document.encode()).hexdigest(),
        "prompt_sha256": hashlib.sha256((FRAME + "\n\n" + document).encode()).hexdigest(),
        "document_words": len(output_words), "signal_words": len(positions),
        "signal_density": len(positions) / len(output_words),
        "full_bag_preserved": Counter(source_words) == Counter(output_words),
        "noise_permutation_changed": shuffled_entries != noise_entries,
        "noise_fixed_points": sum(destination == source_index for destination, source_index
                                  in zip(destinations, [index for index, _ in shuffled_entries])),
    }


def build() -> list[dict]:
    return [build_one(topic, condition) for topic in TOPICS for condition in CONDITIONS]


def write_outputs() -> None:
    frozen = (ROOT / "results/experiment-freeze.json").exists()
    for record in build():
        trial_id = record["trial_id"]; prompt = FRAME + "\n\n" + record["document"]
        metadata = {key: value for key, value in record.items()
                    if key not in {"source_document", "document"}}
        outputs = (
            (ROOT / "development/documents" / f"{trial_id}.txt", record["document"]),
            (ROOT / "development/prompts" / f"{trial_id}.txt", prompt),
            (ROOT / "development/metadata" / f"{trial_id}.json",
             json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"),
        )
        for path, content in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            if frozen and path.exists() and path.read_text() != content:
                raise RuntimeError(f"refusing to overwrite frozen artifact: {path}")
            path.write_text(content)


if __name__ == "__main__":
    write_outputs()
    print(f"wrote {len(build())} deterministic decohered prompts")

