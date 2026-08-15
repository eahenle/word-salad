#!/usr/bin/env python3
"""Generate matched incoherent-interference stimuli at preregistered densities."""

from __future__ import annotations

import argparse
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
SEED_VERSION = "sha256-python-random-v1"
DENSITIES = {
    "d125": {"signal_words": 19, "noise_words": 133, "total_words": 152, "density": 0.125},
    "d250": {"signal_words": 19, "noise_words": 57, "total_words": 76, "density": 0.25},
    "d500": {"signal_words": 19, "noise_words": 19, "total_words": 38, "density": 0.5},
}


def seed(namespace: str, *parts: str) -> dict:
    material = "\n".join(("experiment-4c2", namespace, *parts, SEED_VERSION))
    digest = hashlib.sha256(material.encode()).hexdigest()
    return {"version": SEED_VERSION, "material": material, "sha256": digest,
            "integer": int(digest, 16)}


def source_condition(topic: str, condition: str) -> tuple[list[str], dict]:
    source_id = f"{topic}_{condition}"
    words = (SOURCE_ROOT / "development/documents" / f"{source_id}.txt").read_text().split()
    metadata = json.loads((SOURCE_ROOT / "development/metadata" / f"{source_id}.json").read_text())
    return words, metadata


def canonical_noise_pool(topic: str) -> list[tuple[int, str]]:
    words, metadata = source_condition(topic, "hidden_a")
    positions = set(metadata["signal_positions"])
    pool = [(index, word) for index, word in enumerate(words) if index not in positions]
    expected = Counter(word for _, word in pool)
    for condition in CONDITIONS[1:]:
        other_words, other_metadata = source_condition(topic, condition)
        other_positions = set(other_metadata["signal_positions"])
        other = Counter(word for index, word in enumerate(other_words) if index not in other_positions)
        if other != expected:
            raise AssertionError(f"frozen nonsignal bags differ: {topic}/{condition}")
    order_seed = seed("nested-noise-order", topic)
    shuffled = list(pool); random.Random(order_seed["integer"]).shuffle(shuffled)
    return shuffled


def carrier_mask(topic: str, density_id: str) -> tuple[list[int], dict]:
    configuration = DENSITIES[density_id]; carrier_seed = seed("uniform-carrier", topic, density_id)
    rng = random.Random(carrier_seed["integer"])
    positions = sorted(rng.sample(range(configuration["total_words"]), configuration["signal_words"]))
    return positions, carrier_seed


def run_lengths(mask: list[bool], value: bool) -> list[int]:
    lengths = []; current = 0
    for item in mask:
        if item == value:
            current += 1
        elif current:
            lengths.append(current); current = 0
    if current:
        lengths.append(current)
    return lengths


def build(density_id: str) -> list[dict]:
    if density_id not in DENSITIES:
        raise ValueError(f"unknown density {density_id}")
    configuration = DENSITIES[density_id]; records = []
    for topic in TOPICS:
        noise_order = canonical_noise_pool(topic); selected_noise = noise_order[: configuration["noise_words"]]
        positions, carrier_seed = carrier_mask(topic, density_id); position_set = set(positions)
        mask = [index in position_set for index in range(configuration["total_words"])]
        noise_destinations = [index for index, is_signal in enumerate(mask) if not is_signal]
        for condition in CONDITIONS:
            _, source_metadata = source_condition(topic, condition)
            signal_tokens = source_metadata["signal_tokens"]
            words = [None] * configuration["total_words"]
            for position, token in zip(positions, signal_tokens):
                words[position] = token
            for position, (_, token) in zip(noise_destinations, selected_noise):
                words[position] = token
            if any(token is None for token in words):
                raise AssertionError("unfilled carrier position")
            document = " ".join(words) + "\n"; prompt = FRAME + "\n\n" + document
            trial_id = f"{density_id}_{topic}_{condition}_r01"
            records.append({
                "trial_id": trial_id, "density_id": density_id, "topic": topic,
                "condition": condition, "source_trial_id": f"{topic}_{condition}",
                "hidden_identity": source_metadata["hidden_identity"],
                "expected_answer": source_metadata["expected_answer"],
                "document": document, "signal_tokens": signal_tokens,
                "signal_positions": positions, "signal_mask": mask,
                "noise_destination_indices": noise_destinations,
                "noise_source_indices": [index for index, _ in selected_noise],
                "noise_tokens": [token for _, token in selected_noise],
                "noise_order_seed": seed("nested-noise-order", topic),
                "carrier_seed": carrier_seed,
                "configuration": configuration,
                "longest_signal_run": max(run_lengths(mask, True), default=0),
                "longest_noise_run": max(run_lengths(mask, False), default=0),
                "adjacent_signal_pairs": sum(left and right for left, right in zip(mask, mask[1:])),
                "document_sha256": hashlib.sha256(document.encode()).hexdigest(),
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            })
    return records


def write(density_id: str) -> None:
    stage = ROOT / "development" / density_id; frozen = (stage / "results/stage-freeze.json").exists()
    for record in build(density_id):
        metadata = {key: value for key, value in record.items() if key != "document"}
        prompt = FRAME + "\n\n" + record["document"]
        outputs = ((stage / "documents" / f"{record['trial_id']}.txt", record["document"]),
                   (stage / "prompts" / f"{record['trial_id']}.txt", prompt),
                   (stage / "metadata" / f"{record['trial_id']}.json",
                    json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"))
        for path, content in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            if frozen and path.exists() and path.read_text() != content:
                raise RuntimeError(f"refusing to overwrite frozen stage artifact: {path}")
            path.write_text(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("density", choices=DENSITIES); args = parser.parse_args()
    write(args.density); print(f"wrote {len(build(args.density))} {args.density} prompts")

