#!/usr/bin/env python3
"""Generate natural foreground documents around a frozen sparse word stream."""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from hidden_tasks import PAYLOADS


ROOT = Path(__file__).resolve().parent
FRAME = "Read the following text and give the answer implied by it."

TOPICS = {
    "harbor": {
        "title": "Harbor museum restoration",
        "seed": 4101,
        "prefix": (
            "The old harbor museum reopened its west gallery this spring. "
            "These notes describe the restoration and the people who helped."
        ),
        "suffix": (
            "Together, these modest details give visitors a clear sense of how the waterfront changed."
        ),
        "templates": {
            "Rowan": [
                "Weekend walking tours led by {signal} visit the restored warehouse district.",
                "A newly catalogued ledger lets {signal} trace several former ferry companies.",
                "The surviving winch caption credits {signal} for careful archival research.",
            ],
            "Mira": [
                "A salt-damaged navigation chart gave {signal} several weeks of careful repair work.",
                "Every stage of roof restoration brought {signal} back with a camera.",
            ],
            "Tavi": [
                "Retired dock workers shared stories while {signal} recorded their recollections.",
                "Recent design notes from {signal} favor muted colors for every display case.",
            ],
            "are": ["Several original roof beams {signal} still visible above the quiet ticket desk."],
            "initially": ["The eastern gallery was {signal} a chandlery serving crews from nearby ships."],
            "ordered": ["For the rigging display curators {signal} replica rope from a regional workshop."],
            "exchange": ["A nineteenth-century mercantile {signal} occupied the neighboring brick building for decades."],
            "and": ["Families compare historic maps {signal} recent shoreline photographs beside wide windows."],
            "afterward": ["Workers sealed the repaired masonry {signal} to limit damage from future storms."],
            "relocate": ["Courtyard plans may eventually {signal} one bench as the young trees mature."],
            "beyond": ["On clear mornings fishing boats remain {signal} the tall windows facing east."],
            "output": ["Though modest in scale the generator's {signal} powers a single demonstration lamp."],
            "the": ["Many visitors pause beside {signal} detailed model of an original wooden pier."],
            "central": ["Near the gallery entrance one {signal} display traces rail service to the docks."],
            "name": ["Inside a small donor book each {signal} appears beside a year and hometown."],
        },
        "cover_only": (
            "The old harbor museum reopened its west gallery this spring after a careful roof repair. "
            "Visitors enter through a former warehouse office where ticket clerks once tracked incoming cargo. "
            "Tall windows overlook fishing boats, a stone breakwater, and the channel used by ferries. "
            "A restored winch stands near coils of replica rope and a scale model of the original pier. "
            "Historic maps show how rail lines gradually reached the waterfront during the nineteenth century. "
            "Nearby photographs document shipwrights, chandlers, market vendors, and families waiting for passage. "
            "The eastern room now holds navigation charts that conservators repaired after years of salt damage. "
            "Muted cases and low lighting protect fragile ledgers without making labels difficult to read. "
            "A courtyard offers benches beneath young trees, while a small generator powers one demonstration lamp. "
            "Weekend guides add stories collected from retired dock workers throughout the region. "
            "A donor book near reception lists hometowns beside each contribution. "
            "The result is a modest exhibition that connects working lives with changes along the shore."
        ),
    },
    "ceramics": {
        "title": "Regional ceramics exhibition",
        "seed": 4102,
        "prefix": (
            "A regional ceramics museum opened a new study gallery beside its public studio. "
            "The display focuses on practical vessels and the craft behind them."
        ),
        "suffix": (
            "Taken together, the gallery's quiet details make a familiar household craft feel newly vivid."
        ),
        "templates": {
            "Rowan": [
                "During Saturday workshops curator {signal} demonstrates how early potters prepared clay.",
                "A regional archive recently sent {signal} photographs from a closed riverside kiln.",
                "One wall label prepared by {signal} describes repairs to a cracked vessel.",
            ],
            "Mira": [
                "For the blue stoneware case {signal} selected a gently angled shelf.",
                "A recorded interview features {signal} discussing glaze tests from last winter.",
            ],
            "Tavi": [
                "At the public studio host {signal} welcomes families during monthly open houses.",
                "Recent catalog notes from {signal} emphasize ordinary pieces used in households.",
            ],
            "are": ["Several tiny firing marks {signal} visible beneath the largest serving bowls."],
            "initially": ["The west alcove was {signal} reserved for temporary loans from nearby schools."],
            "ordered": ["Before installation the team {signal} custom mounts from a conservation supplier."],
            "exchange": ["An old village trade {signal} once stood near the excavated kiln site."],
            "and": ["Visitors compare glossy porcelain {signal} rough earthenware under the same soft lights."],
            "afterward": ["Technicians adjusted each support {signal} to keep the heavier jars perfectly level."],
            "relocate": ["Future renovation plans may {signal} the reading bench closer to natural light."],
            "beyond": ["Several studio photographs continue {signal} the main gallery toward a quiet corridor."],
            "output": ["A small electric kiln has limited {signal} but handles demonstration tiles reliably."],
            "the": ["Children often sketch beside {signal} display of bowls from coastal workshops."],
            "central": ["Near two arched windows a {signal} case presents vessels used for storing grain."],
            "name": ["On each loan card the maker's {signal} appears below a brief regional note."],
        },
        "cover_only": (
            "A regional ceramics museum opened a new study gallery beside its popular public studio. "
            "The exhibition begins with rough earthenware jars used for grain, oil, and preserved fruit. "
            "Across the room, glossy porcelain cups sit on gently angled shelves under soft lighting. "
            "Small firing marks beneath several bowls reveal how pieces rested inside crowded kilns. "
            "Wall photographs show riverside workshops that closed before modern electric equipment arrived. "
            "A recorded interview describes winter glaze tests and the patience required for consistent color. "
            "Custom mounts support cracked vessels while allowing visitors to see old repairs. "
            "The west alcove holds temporary loans selected by nearby schools and community studios. "
            "Children sketch coastal bowls at a broad table near two arched windows. "
            "Monthly open houses include clay preparation demonstrations for families. "
            "Loan cards identify makers and regions without crowding the cases. "
            "The calm arrangement keeps attention on useful objects and the hands that shaped them."
        ),
    },
    "garden": {
        "title": "Community garden seasonal notes",
        "seed": 4103,
        "prefix": (
            "The neighborhood garden has entered its busiest season beside the community greenhouse. "
            "A recent bulletin describes routine work and several small improvements."
        ),
        "suffix": (
            "These steady efforts keep the shared space welcoming without changing its informal character."
        ),
        "templates": {
            "Rowan": [
                "During spring workdays volunteer {signal} checks seedlings along the shaded north fence.",
                "An illustrated planting log lets {signal} compare harvest dates across recent seasons.",
                "New compost signs prepared by {signal} use simple drawings for younger visitors.",
            ],
            "Mira": [
                "Beside the tool shed volunteer {signal} maintains a small bed of medicinal herbs.",
                "Each monthly newsletter includes {signal} reporting which vegetables reached the pantry.",
            ],
            "Tavi": [
                "Before weekend classes instructor {signal} arranges clean gloves near the washing station.",
                "An autumn workshop led by {signal} focused on saving seeds from beans.",
            ],
            "are": ["Several rain barrels {signal} connected to gutters along the community greenhouse."],
            "initially": ["The eastern plot was {signal} planted with peas and cool-weather greens."],
            "ordered": ["For the orchard edge volunteers {signal} bare-root shrubs from a local nursery."],
            "exchange": ["A neighborhood seed {signal} draws dozens of gardeners near the first frost."],
            "and": ["Families grow tomatoes {signal} climbing beans on sturdy cedar frames."],
            "afterward": ["Gardeners watered the transplants {signal} to settle soil around each root."],
            "relocate": ["Next season coordinators may {signal} the picnic table beneath a larger tree."],
            "beyond": ["A narrow pollinator strip continues {signal} the main beds toward the sidewalk."],
            "output": ["At midday the solar pump's {signal} keeps a shallow birdbath circulating."],
            "the": ["Visitors usually gather beside {signal} mural painted across the storage shed."],
            "central": ["Between two herb beds a {signal} path allows wheelbarrows to pass easily."],
            "name": ["On every wooden plot sign the gardener's {signal} remains visible through summer."],
        },
        "cover_only": (
            "The neighborhood garden has entered its busiest season beside the community greenhouse. "
            "Peas and cool-weather greens still fill the eastern plot, while tomatoes climb cedar frames nearby. "
            "Rain barrels collect water from gutters and feed a shallow birdbath through a small solar pump. "
            "A pollinator strip follows the sidewalk with herbs, grasses, and flowers that bloom in succession. "
            "Volunteers recently added compost signs with simple drawings for younger visitors. "
            "Bare-root shrubs along the orchard edge survived their first dry week with regular watering. "
            "Weekend classes use the washing station beside the tool shed before handling fresh produce. "
            "A planting log compares harvest dates and notes which vegetables reached the local pantry. "
            "Families gather near a painted mural while children inspect beans saved for autumn workshops. "
            "The picnic table remains beneath a young tree that will eventually provide more shade. "
            "Wooden plot signs remain legible despite summer rain and bright sun. "
            "Routine care keeps the shared space useful, informal, and welcoming."
        ),
    },
}


def occurrence_keys(tokens: tuple[str, ...] | list[str]) -> list[tuple[str, int]]:
    counts: defaultdict[str, int] = defaultdict(int)
    keys = []
    for token in tokens:
        counts[token] += 1
        keys.append((token, counts[token]))
    return keys


def render(topic: str, tokens: list[str] | tuple[str, ...]) -> tuple[str, list[int], list[dict]]:
    specification = TOPICS[topic]
    words = specification["prefix"].split()
    sentences = [specification["prefix"]]
    positions: list[int] = []
    carrier: list[dict] = []
    counts: defaultdict[str, int] = defaultdict(int)
    for sequence_index, token in enumerate(tokens):
        counts[token] += 1
        occurrence = counts[token]
        template = specification["templates"][token][occurrence - 1]
        if template.count("{signal}") != 1:
            raise AssertionError(f"bad template marker: {topic}/{token}/{occurrence}")
        before, after = template.split("{signal}")
        before_words, after_words = before.split(), after.split()
        position = len(words) + len(before_words)
        sentence = before + token + after
        sentence_words = sentence.split()
        if sentence_words[len(before_words)] != token:
            raise AssertionError("signal token is not a standalone whitespace word")
        words.extend(sentence_words)
        positions.append(position)
        carrier.append({"sequence_index": sequence_index, "position": position,
                        "token": token, "occurrence": occurrence,
                        "sentence": sentence})
        sentences.append(sentence)
    sentences.append(specification["suffix"])
    words.extend(specification["suffix"].split())
    document = " ".join(sentences) + "\n"
    if document.split() != words:
        raise AssertionError("document assembly mismatch")
    return document, positions, carrier


def build() -> list[dict]:
    records: list[dict] = []
    for topic, specification in TOPICS.items():
        conditions = {"hidden_a": list(PAYLOADS["A"]), "hidden_b": list(PAYLOADS["B"])}
        shuffled = list(PAYLOADS["A"])
        random.Random(specification["seed"]).shuffle(shuffled)
        if tuple(shuffled) in PAYLOADS.values():
            raise AssertionError("scramble accidentally intact")
        conditions["scrambled"] = shuffled
        documents = {}
        for condition, tokens in conditions.items():
            document, positions, carrier = render(topic, tokens)
            documents[condition] = document
            records.append({
                "trial_id": f"{topic}_{condition}", "topic": topic,
                "topic_title": specification["title"], "condition": condition,
                "hidden_identity": {"hidden_a": "A", "hidden_b": "B"}.get(condition),
                "expected_answer": {"hidden_a": "Rowan", "hidden_b": "Mira"}.get(condition),
                "document": document, "signal_tokens": tokens,
                "signal_positions": positions, "carrier": carrier,
                "scramble_seed": specification["seed"] if condition == "scrambled" else None,
            })
        if not (Counter(documents["hidden_a"].split()) == Counter(documents["hidden_b"].split())
                == Counter(documents["scrambled"].split())):
            raise AssertionError(f"full-document bag mismatch for {topic}")
        cover = specification["cover_only"].strip() + "\n"
        records.append({
            "trial_id": f"{topic}_cover_only", "topic": topic,
            "topic_title": specification["title"], "condition": "cover_only",
            "hidden_identity": None, "expected_answer": None,
            "document": cover, "signal_tokens": [], "signal_positions": [],
            "carrier": [], "scramble_seed": None,
        })
    return sorted(records, key=lambda record: record["trial_id"])


def write_outputs() -> None:
    for record in build():
        document_path = ROOT / "development/documents" / f"{record['trial_id']}.txt"
        metadata_path = ROOT / "development/metadata" / f"{record['trial_id']}.json"
        prompt = FRAME + "\n\n" + record["document"]
        metadata = {key: value for key, value in record.items() if key != "document"}
        metadata.update({
            "document_sha256": hashlib.sha256(record["document"].encode()).hexdigest(),
            "document_words": len(record["document"].split()),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt_words": len(prompt.split()),
            "frame": FRAME,
        })
        for path, content in (
            (document_path, record["document"]),
            (metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            if (ROOT / "results/experiment-freeze.json").exists() and path.exists() and path.read_text() != content:
                raise RuntimeError(f"refusing to overwrite frozen stimulus: {path}")
            path.write_text(content)


if __name__ == "__main__":
    write_outputs()
    print(f"wrote {len(build())} development documents")
