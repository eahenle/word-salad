#!/usr/bin/env python3
"""Generate paired equal-bag stimuli for Experiment 2."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from simulate import build_payload, load_protocol, simulate, validate_and_write


GENERATOR_VERSION = "q2-equal-bag-v1"
ARMS = ("constrained", "explanation")
LANE_COUNTS = (2, 4)
SEEDS = tuple(range(1, 21))


@dataclass(frozen=True)
class Task:
    neutral_id: str
    trial_id: str
    arm: str
    condition: str
    payload_identity: str | None
    lanes: int
    seed: int
    prompt: str
    metadata: dict

    @property
    def variant(self) -> str:
        """Compatibility name for the shared result schema."""
        return self.arm


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def derived_seed(*parts: object) -> int:
    material = GENERATOR_VERSION + "|" + "|".join(str(part) for part in parts)
    return int.from_bytes(hashlib.sha256(material.encode()).digest()[:16], "big")


def occurrence_ids(words: Sequence[str]) -> list[tuple[str, int]]:
    counts: dict[str, int] = defaultdict(int)
    output = []
    for word in words:
        output.append((word, counts[word]))
        counts[word] += 1
    return output


def payloads_for_arm(root: Path, arm: str) -> tuple[dict[str, str], dict[str, dict]]:
    _, operations, orders = load_protocol(root)
    template_name = (
        "payload_common.txt" if arm == "constrained" else "payload_common_explanation.txt"
    )
    template = (root / template_name).read_text(encoding="utf-8").strip()
    payloads = {
        identity: build_payload(template, operations, order)
        for identity, order in orders.items()
    }
    if Counter(payloads["A"].split()) != Counter(payloads["B"].split()):
        raise AssertionError(f"{arm} A/B word bags differ")
    answers = {identity: simulate(operations, order) for identity, order in orders.items()}
    return payloads, answers


def geometry(
    word_count: int,
    order_a: Sequence[int],
    order_b: Sequence[int],
    lanes: int,
    seed: int,
) -> tuple[int, list[list[int]]]:
    phase = random.Random(derived_seed("phase", lanes, seed)).randrange(lanes)
    forbidden = {tuple(order_a), tuple(order_b)}
    permutations = []
    for lane in range(lanes):
        if lane == phase:
            permutations.append([])
            continue
        base = list(range(word_count))
        attempt = 0
        while True:
            candidate = base.copy()
            random.Random(derived_seed("distractor", lanes, seed, lane, attempt)).shuffle(
                candidate
            )
            if tuple(candidate) not in forbidden:
                break
            attempt += 1
        permutations.append(candidate)
    return phase, permutations


def task_coordinates() -> list[tuple[str, str, str | None, int, int]]:
    coordinates = []
    for arm in ARMS:
        for identity in ("A", "B"):
            for seed in SEEDS:
                coordinates.append((arm, "clean", identity, 1, seed))
        for lanes in LANE_COUNTS:
            for identity in ("A", "B"):
                for seed in SEEDS:
                    coordinates.append((arm, "signal", identity, lanes, seed))
            for seed in SEEDS:
                coordinates.append((arm, "all_shuffled", None, lanes, seed))
    return coordinates


def build_tasks(root: Path) -> list[Task]:
    validate_and_write(root)
    tasks = []
    for index, (arm, condition, identity, lanes, seed) in enumerate(
        task_coordinates(), start=1
    ):
        payloads, answers = payloads_for_arm(root, arm)
        words_by_identity = {key: value.split() for key, value in payloads.items()}
        ids_by_identity = {
            key: occurrence_ids(words) for key, words in words_by_identity.items()
        }
        canonical_ids = ids_by_identity["A"]
        canonical_index = {occurrence: position for position, occurrence in enumerate(canonical_ids)}
        order_indices = {
            key: [canonical_index[occurrence] for occurrence in ids]
            for key, ids in ids_by_identity.items()
        }
        canonical_words = [word for word, _ in canonical_ids]
        phase = None
        permutations: list[list[int]] = []
        if condition == "clean":
            serialized = words_by_identity[identity]
            phase = 0
            permutations = [order_indices[identity]]
        else:
            phase, distractors = geometry(
                len(canonical_words),
                order_indices["A"],
                order_indices["B"],
                lanes,
                seed,
            )
            if condition == "signal":
                permutations = [
                    order_indices[identity] if lane == phase else distractors[lane]
                    for lane in range(lanes)
                ]
            else:
                # Use another deterministic shuffled lane at the nominal phase.
                _, phase_distractors = geometry(
                    len(canonical_words),
                    order_indices["A"],
                    order_indices["B"],
                    lanes,
                    derived_seed("all-shuffled-phase", seed),
                )
                phase_lane = next(value for value in phase_distractors if value)
                permutations = [
                    phase_lane if lane == phase else distractors[lane]
                    for lane in range(lanes)
                ]
            serialized = [
                canonical_words[permutations[lane][position]]
                for position in range(len(canonical_words))
                for lane in range(lanes)
            ]
        prompt = " ".join(serialized)
        neutral_id = f"r{index:04d}"
        geometry_value = {
            "phase": phase,
            "distractors": [
                permutation if condition == "all_shuffled" or lane != phase else None
                for lane, permutation in enumerate(permutations)
            ],
        }
        metadata = {
            "neutral_id": neutral_id,
            "trial_id": neutral_id,
            "arm": arm,
            "condition": condition,
            "payload_identity": identity,
            "lanes": lanes,
            "seed": seed,
            "signal_phase": phase if condition == "signal" else None,
            "nominal_phase": phase,
            "prompt_words": len(serialized),
            "payload_words": len(canonical_words),
            "prompt_sha256": sha256_text(prompt),
            "payload_a_sha256": sha256_text(payloads["A"]),
            "payload_b_sha256": sha256_text(payloads["B"]),
            "canonical_word_bag_sha256": sha256_text(
                json.dumps(sorted(Counter(canonical_words).items()), separators=(",", ":"))
            ),
            "geometry_sha256": sha256_text(
                json.dumps(geometry_value, separators=(",", ":"))
            ),
            "permutations": permutations,
            "signal_order_indices": order_indices.get(identity) if identity else None,
            "answer_identity": identity if condition in ("clean", "signal") else None,
            "generator_version": GENERATOR_VERSION,
        }
        tasks.append(
            Task(
                neutral_id=neutral_id,
                trial_id=neutral_id,
                arm=arm,
                condition=condition,
                payload_identity=identity,
                lanes=lanes,
                seed=seed,
                prompt=prompt,
                metadata=metadata,
            )
        )
    return tasks


def write_tasks(root: Path, tasks: Sequence[Task]) -> None:
    for task in tasks:
        prompt_dir = root / "prompts" / task.arm
        metadata_dir = root / "metadata" / task.arm
        prompt_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = prompt_dir / f"{task.neutral_id}.txt"
        metadata_path = metadata_dir / f"{task.neutral_id}.json"
        rendered_metadata = json.dumps(task.metadata, indent=2) + "\n"
        if prompt_path.exists() and prompt_path.read_text(encoding="utf-8") != task.prompt:
            raise FileExistsError(f"refusing to replace mismatched prompt: {prompt_path}")
        if metadata_path.exists() and metadata_path.read_text(encoding="utf-8") != rendered_metadata:
            raise FileExistsError(f"refusing to replace mismatched metadata: {metadata_path}")
        prompt_path.write_text(task.prompt, encoding="utf-8")
        metadata_path.write_text(rendered_metadata, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    tasks = build_tasks(args.root)
    write_tasks(args.root, tasks)
    print(f"wrote or verified {len(tasks)} Experiment 2 prompts")


if __name__ == "__main__":
    main()
