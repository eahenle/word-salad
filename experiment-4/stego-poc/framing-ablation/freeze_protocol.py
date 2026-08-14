#!/usr/bin/env python3
"""Freeze Arm A context, references, schema, image, and advancement rule."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from runtime import DISABLED_FEATURES, EFFORT, IMAGE, MODEL
from validate import ROOT, validate


def sha256(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    validation = validate()
    sources = ("README.md", "frozen-references.json", "tool-schema.json", "contexts/raw.txt", "contexts/summarize-only.txt",
               "container/Dockerfile", "container/marker_server.py", "runtime.py", "validate.py")
    freeze = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(), "arm": "A_raw_text",
              "model": MODEL, "reasoning": EFFORT, "image": IMAGE,
              "raw_context": {"custom_developer_instructions": None, "prefix": "", "suffix": "",
                              "user_message": "exact frozen document bytes only"},
              "development_gate": {"expected_individuals_at_least": 3,
                                   "or_complete_pairs_at_least": 1,
                                   "counterpart_errors_exactly": 0},
              "scheduled_trials": 4, "score_after_full_freeze": True,
              "disabled_codex_features": list(DISABLED_FEATURES),
              "tool": {"name": validation["tool_name"], "description": validation["tool_description"],
                       "allowed_labels": validation["allowed_labels"],
                       "implementation_sha256": sha256(ROOT / "container/marker_server.py")},
              "prompt_hashes": {row["trial_id"]: row["raw_prompt_sha256"] for row in validation["document_records"]},
              "source_hashes": {name: sha256(ROOT / name) for name in sources}}
    path = ROOT / "results/protocol-freeze.json"; content = json.dumps(freeze, indent=2) + "\n"
    if path.exists():
        previous = json.loads(path.read_text()); comparable = dict(freeze); comparable["frozen_at_utc"] = previous["frozen_at_utc"]
        if previous != comparable: raise RuntimeError("existing protocol freeze differs")
        print("verified existing protocol freeze"); return
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
    print(f"froze {len(freeze['prompt_hashes'])} raw prompts")


if __name__ == "__main__": main()
