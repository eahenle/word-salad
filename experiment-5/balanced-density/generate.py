#!/usr/bin/env python3
"""Generate all frozen balanced-density stages with matched A/B/control bags."""

from __future__ import annotations

import hashlib
import json
import random
import string
from collections import Counter
from pathlib import Path

from hidden_tasks import ANSWERS, PAYLOAD_A, PAYLOAD_B, PAYLOAD_INDICES, SYMBOLS, validate_tasks


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
FRAME = "Read the following text and give the answer implied by it."
STAGES = {
    "d075": 293,
    "d125": 176,
    "d250": 88,
    "d500": 44,
}
SEEDS = (1, 2, 3)
CONDITIONS = ("hidden_a", "hidden_b", "scrambled")
NOISE_SOURCES = (
    REPO / "experiment-4/dual-channel/development/documents/harbor_cover_only.txt",
    REPO / "experiment-4/dual-channel/development/documents/ceramics_cover_only.txt",
    REPO / "experiment-4/dual-channel/development/documents/garden_cover_only.txt",
)


def seed_int(*parts: object) -> tuple[str, int]:
    material = "\n".join(map(str, ("experiment-5-balanced-density-v1",) + parts))
    digest = hashlib.sha256(material.encode()).hexdigest()
    return material, int(digest, 16)


def normalized(token: str) -> str:
    return token.strip(string.punctuation).casefold()


def noise_pool() -> list[str]:
    hidden = {normalized(token) for token in PAYLOAD_A}
    words = []
    for path in NOISE_SOURCES:
        words.extend(path.read_text().split())
    words = [word for word in words if normalized(word) not in hidden]
    if len(words) < max(STAGES.values()) - len(PAYLOAD_A):
        raise RuntimeError("insufficient heterogeneous noise words")
    if any(normalized(word) in {symbol.casefold() for symbol in SYMBOLS} for word in words):
        raise RuntimeError("candidate symbol leaked into noise pool")
    return words


def b_indices() -> list[int]:
    return PAYLOAD_INDICES["B"]


def scrambled_indices(seed: int) -> list[int]:
    material, value = seed_int("scrambled", seed)
    indices = list(range(len(PAYLOAD_A)))
    rng = random.Random(value)
    while True:
        rng.shuffle(indices)
        rendered = [PAYLOAD_A[index] for index in indices]
        if rendered != PAYLOAD_A and rendered != PAYLOAD_B:
            return indices.copy()


def render(indices: list[int]) -> list[str]:
    return [PAYLOAD_A[index] for index in indices]


def longest_run(mask: list[bool], value: bool) -> int:
    best = current = 0
    for item in mask:
        current = current + 1 if item == value else 0
        best = max(best, current)
    return best


def generate_stage(stage: str, total_words: int, pool: list[str]) -> list[dict]:
    stage_root = ROOT / "stages" / stage
    for directory in ("documents", "prompts", "metadata"):
        (stage_root / directory).mkdir(parents=True, exist_ok=True)
    rows = []
    signal_words = len(PAYLOAD_A)
    noise_words = total_words - signal_words
    for seed in SEEDS:
        noise_material, noise_seed = seed_int("noise-order", seed)
        ordered_noise = pool.copy()
        random.Random(noise_seed).shuffle(ordered_noise)
        noise = ordered_noise[:noise_words]
        carrier_material, carrier_seed = seed_int("carrier", stage, seed)
        positions = sorted(random.Random(carrier_seed).sample(range(total_words), signal_words))
        position_set = set(positions)
        carrier_mask = [index in position_set for index in range(total_words)]
        mask_statistics = {
            "first_signal_position": positions[0],
            "last_signal_position": positions[-1],
            "adjacent_signal_pairs": sum(right == left + 1 for left, right in zip(positions, positions[1:])),
            "longest_signal_run": longest_run(carrier_mask, True),
            "longest_noise_run": longest_run(carrier_mask, False),
        }
        condition_indices = {
            "hidden_a": PAYLOAD_INDICES["A"],
            "hidden_b": b_indices(),
            "scrambled": scrambled_indices(seed),
        }
        rendered_documents = {}
        for condition in CONDITIONS:
            trial_id = f"{stage}_s{seed:02d}_{condition}"
            indices = condition_indices[condition]
            signal = render(indices)
            document = [None] * total_words
            for position, token in zip(positions, signal):
                document[position] = token
            noise_iterator = iter(noise)
            for index, value in enumerate(document):
                if value is None:
                    document[index] = next(noise_iterator)
            rendered_documents[condition] = document
            document_text = " ".join(document) + "\n"
            prompt_text = FRAME + "\n\n" + document_text
            document_path = stage_root / "documents" / f"{trial_id}.txt"
            prompt_path = stage_root / "prompts" / f"{trial_id}.txt"
            document_path.write_text(document_text)
            prompt_path.write_text(prompt_text)
            identity = "A" if condition == "hidden_a" else "B" if condition == "hidden_b" else None
            metadata = {
                "trial_id": trial_id,
                "stage": stage,
                "seed": seed,
                "condition": condition,
                "hidden_identity": identity,
                "expected_answer": " ".join(ANSWERS[identity]) if identity else None,
                "signal_source_indices": indices,
                "signal_words_rendered": signal,
                "signal_positions": positions,
                "signal_words": signal_words,
                "noise_words": noise_words,
                "document_words": total_words,
                "actual_density": signal_words / total_words,
                "mask_statistics": mask_statistics,
                "carrier_seed": {"material": carrier_material, "sha256": hashlib.sha256(carrier_material.encode()).hexdigest(), "integer": carrier_seed},
                "noise_seed": {"material": noise_material, "sha256": hashlib.sha256(noise_material.encode()).hexdigest(), "integer": noise_seed},
                "document_sha256": hashlib.sha256(document_text.encode()).hexdigest(),
                "prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest(),
                "prompt_words": len(prompt_text.split()),
            }
            (stage_root / "metadata" / f"{trial_id}.json").write_text(json.dumps(metadata, indent=2) + "\n")
            rows.append(metadata)
        bags = {condition: Counter(document) for condition, document in rendered_documents.items()}
        if not (bags["hidden_a"] == bags["hidden_b"] == bags["scrambled"]):
            raise RuntimeError(f"full-document bag mismatch: {stage}/seed{seed}")
    order_material, order_seed = seed_int("query-order", stage)
    query_order = [row["trial_id"] for row in rows]
    random.Random(order_seed).shuffle(query_order)
    manifest = {
        "stage": stage,
        "signal_words": signal_words,
        "noise_words": noise_words,
        "document_words": total_words,
        "actual_density": signal_words / total_words,
        "query_order_seed": {"material": order_material, "sha256": hashlib.sha256(order_material.encode()).hexdigest(), "integer": order_seed},
        "query_order": query_order,
        "trials": rows,
    }
    (stage_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return rows


def main() -> None:
    validation = validate_tasks()
    pool = noise_pool()
    all_rows = []
    for stage, total_words in STAGES.items():
        all_rows.extend(generate_stage(stage, total_words, pool))
    source_hashes = {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in NOISE_SOURCES}
    (ROOT / "results").mkdir(parents=True, exist_ok=True)
    (ROOT / "results/generation-summary.json").write_text(json.dumps({
        "generator_version": "experiment-5-balanced-density-v1",
        "task_validation": validation,
        "stages": STAGES,
        "seeds": list(SEEDS),
        "scheduled_trials": len(all_rows),
        "noise_source_hashes": source_hashes,
        "noise_pool_words_after_exclusion": len(pool),
        "all_prompts_generated_before_inference": True,
    }, indent=2) + "\n")
    print(f"generated {len(all_rows)} frozen-candidate prompts across {len(STAGES)} stages")


if __name__ == "__main__":
    main()
