#!/usr/bin/env python3
"""Print and validate the deterministic full-state answer keys."""

from __future__ import annotations

import json

from hidden_tasks import ANSWERS, PLANS, validate_tasks


def main() -> None:
    validation = validate_tasks()
    print(json.dumps({
        "plans": {key: list(value) for key, value in PLANS.items()},
        "answers": {key: " ".join(value) for key, value in ANSWERS.items()},
        "validation": validation,
    }, indent=2))


if __name__ == "__main__":
    main()
