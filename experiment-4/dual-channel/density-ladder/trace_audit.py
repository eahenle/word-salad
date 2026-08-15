#!/usr/bin/env python3
"""Audit observable strategies after all authorized density stages finish."""

from __future__ import annotations

import json
from collections import Counter

from generate import ROOT
from runtime import atomic_json


STRUCTURE=("structure","scrambl","shuffl","extraction","transposition","word order","jumbled","hidden","encoded")
STRIDE=("every nth","every other","stride","interleav","residue")
TOOL={"command_execution","mcp_tool_call","file_change","web_search","browser_action","computer_action","tool_call"}


def main() -> None:
    records=[]
    for density in ("d125","d250"):
        stage=ROOT/"development"/density
        if not (stage/"results/trials.jsonl").exists(): continue
        trials=[json.loads(line) for line in (stage/"results/trials.jsonl").read_text().splitlines()]
        for trial in trials:
            items=[]
            for line in (ROOT/trial["trace_file"]).read_text().splitlines():
                event=json.loads(line)
                if event.get("type")=="item.completed": items.append(event.get("item",{}))
            messages=[str(item.get("text","")) for item in items if item.get("type")=="agent_message"]
            text="\n".join(messages).lower(); tools=[item.get("type") for item in items if item.get("type") in TOOL]
            records.append({"trial_id":trial["trial_id"],"density_id":density,"condition":trial["condition"],
                "classification":trial["classification"],"semantic_success":trial["semantic_success"],
                "observable_messages":messages,"explicit_structure_language":any(term in text for term in STRUCTURE),
                "explicit_stride_testing":any(term in text for term in STRIDE),"tool_item_types":tools})
    summary={"audited_after_all_authorized_stages":True,"trials":len(records),
        "classification_counts":dict(sorted(Counter(row["classification"] for row in records).items())),
        "explicit_structure_trials":sum(row["explicit_structure_language"] for row in records),
        "explicit_stride_testing_trials":sum(row["explicit_stride_testing"] for row in records),
        "trials_with_tool_items":sum(bool(row["tool_item_types"]) for row in records),
        "records":records,"private_chain_of_thought_claimed":False}
    atomic_json(ROOT/"results/trace-strategy-audit.json",summary); print(json.dumps({k:v for k,v in summary.items() if k!="records"},indent=2))


if __name__ == "__main__": main()

