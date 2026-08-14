#!/usr/bin/env python3
"""Prepare a blinded, benign naturalness-rating packet; collect no responses."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from cover_generator import build


ORDINARY = [
    "A neighborhood bakery tests one seasonal loaf each month. Staff compare crust color, texture, and cooling time before adding the recipe to the weekend menu.",
    "Commuters along the river route can choose a shaded footpath or a frequent local bus. Both options reach the central station before the morning markets open.",
    "The astronomy club meets after sunset to identify bright planets and compare telescope views. New members begin with the moon because its larger features are easy to locate.",
    "A local history group is cataloging photographs of the old railway district. Volunteers add approximate dates and short captions after comparing storefront signs and street maps.",
    "Woodworking students start by measuring scrap boards and practicing straight cuts. Their first finished project is a small tray designed to teach sanding and simple joinery.",
]


def main() -> None:
    root = Path(__file__).resolve().parent; output = root / "human-rating"; output.mkdir(parents=True, exist_ok=True)
    heldout = build("heldout"); selected = []
    for index, topic in enumerate(sorted({item.topic_id for item in heldout})):
        conditions = {item.condition: item for item in heldout if item.topic_id == topic}
        hidden = conditions["hidden_A" if index % 2 == 0 else "hidden_B"]
        selected.extend((("hidden_cover", topic, hidden.document),
                         ("benign_cover", topic, conditions["benign"].document),
                         ("ordinary_control", f"o{index + 1}", ORDINARY[index])))
    random.Random(44020).shuffle(selected)
    packet = []; key = []
    for number, (condition, source, passage) in enumerate(selected, 1):
        rating_id = f"r{number:03d}"; packet.append({"rating_id": rating_id, "passage": passage})
        key.append({"rating_id": rating_id, "condition": condition, "source": source})
    with (output / "packet.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("rating_id", "passage"), lineterminator="\n")
        writer.writeheader(); writer.writerows(packet)
    with (output / "response-template.csv").open("w", newline="") as handle:
        fields = ("rater_id", "rating_id", "reads_naturally_1_to_5", "appears_corrupted_yes_no",
                  "appears_unusually_constrained_yes_no", "apparent_topic", "optional_comment")
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n"); writer.writeheader()
    (output / "coordinator-key.json").write_text(json.dumps(key, indent=2) + "\n")
    print(f"wrote {len(packet)} blinded passages; no human ratings were fabricated or collected")


if __name__ == "__main__":
    main()
