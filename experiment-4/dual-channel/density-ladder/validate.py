#!/usr/bin/env python3
"""Fail-closed validation of one density-ladder stage."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

from generate import CONDITIONS, DENSITIES, FRAME, ROOT, SOURCE_ROOT, TOPICS, build, canonical_noise_pool


SOURCE_4C_COMMIT = "d5dc2a837086a06b85361130c7e56ea957c9a650"
SOURCE_4C1_COMMIT = "6c9e1bdf1d7c31a6dcb702391a5673e7e2636475"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_simulator():
    source = SOURCE_ROOT / "simulate.py"
    freeze = json.loads((SOURCE_ROOT / "results/experiment-freeze.json").read_text())
    if sha256(source) != freeze["source_hashes"]["simulate.py"]:
        raise RuntimeError("frozen simulator hash mismatch")
    sys.path.insert(0, str(SOURCE_ROOT))
    spec = importlib.util.spec_from_file_location("experiment_4c_density_simulator", source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def validate(density_id: str) -> dict:
    configuration = DENSITIES[density_id]; records = build(density_id); simulator = load_simulator()
    stage = ROOT / "development" / density_id; failures = []; rows = []
    for topic in TOPICS:
        cells = {record["condition"]: record for record in records if record["topic"] == topic}
        bags = [Counter(cells[condition]["document"].split()) for condition in CONDITIONS]
        if not bags[0] == bags[1] == bags[2]:
            failures.append(f"{topic}: full A/B/scrambled bags differ")
        masks = [cells[condition]["signal_positions"] for condition in CONDITIONS]
        if not masks[0] == masks[1] == masks[2]:
            failures.append(f"{topic}: carrier masks differ across conditions")
        if density_id != "d125":
            larger_pool = canonical_noise_pool(topic)[: configuration["noise_words"]]
            if [entry[0] for entry in larger_pool] != cells["hidden_a"]["noise_source_indices"]:
                failures.append(f"{topic}: nested noise selection mismatch")
    for record in records:
        words = record["document"].split(); positions = record["signal_positions"]
        extracted = [words[position] for position in positions]
        prompt_path = stage / "prompts" / f"{record['trial_id']}.txt"
        checks = {
            "total_word_count_exact": len(words) == configuration["total_words"],
            "signal_count_exact": len(positions) == configuration["signal_words"] == len(set(positions)),
            "noise_count_exact": len(record["noise_tokens"]) == configuration["noise_words"],
            "density_exact": len(positions) / len(words) == configuration["density"],
            "signal_extraction_exact": extracted == record["signal_tokens"],
            "positions_sorted_unique_in_range": positions == sorted(set(positions)) and positions[-1] < len(words),
            "prompt_exact": prompt_path.read_text() == FRAME + "\n\n" + record["document"],
            "prompt_hash_exact": sha256(prompt_path) == record["prompt_sha256"],
        }
        if record["hidden_identity"]:
            checks["answer_resimulated"] = simulator.simulate(tuple(extracted)) == record["expected_answer"]
        else:
            payloads = json.loads((SOURCE_ROOT / "results/experiment-freeze.json").read_text())["payloads"]
            checks["scrambled_not_intact"] = extracted not in [payloads[key].split() for key in ("A", "B")]
            checks["scrambled_bag_equal"] = Counter(extracted) == Counter(payloads["A"].split())
        for name, passed in checks.items():
            if not passed:
                failures.append(f"{record['trial_id']}: {name}")
        rows.append({"trial_id": record["trial_id"], "topic": record["topic"],
                     "condition": record["condition"], "checks": checks,
                     "prompt_sha256": record["prompt_sha256"],
                     "document_sha256": record["document_sha256"],
                     "signal_positions": positions,
                     "longest_signal_run": record["longest_signal_run"],
                     "longest_noise_run": record["longest_noise_run"],
                     "adjacent_signal_pairs": record["adjacent_signal_pairs"]})
    report = {"passed": not failures, "failures": failures, "density_id": density_id,
              "configuration": configuration, "scheduled_trials": 9,
              "source_4c_commit": SOURCE_4C_COMMIT, "source_4c1_commit": SOURCE_4C1_COMMIT,
              "topics": list(TOPICS), "conditions": list(CONDITIONS), "records": rows}
    if failures:
        raise AssertionError("\n".join(failures))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("density", choices=DENSITIES)
    print(json.dumps(validate(parser.parse_args().density), indent=2))
