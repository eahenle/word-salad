#!/usr/bin/env python3
"""Post-freeze correction layer for display labels and observable strategy evidence."""

from __future__ import annotations

import json
from collections import Counter

from generate import ROOT
from runtime import atomic_bytes, atomic_json


STRUCTURE_TERMS=("word order","word-order","scrambl","interleav","reconstruct","transposition","extraction")
CONCRETE_STRIDE_TERMS=("every nth","every other","fixed stride","residue class","extract every","stride ")


def main() -> None:
    stage=ROOT/"development/d125"; trials=[json.loads(line) for line in (stage/"results/trials.jsonl").read_text().splitlines()]
    audited=[]; strategy=[]
    for row in trials:
        updated=dict(row)
        if row["condition"]=="scrambled" and row["control_target_selection"]:
            updated["audited_classification"]="control_target_answer"
        else: updated["audited_classification"]=row["classification"]
        audited.append(updated)
        messages=[]
        for line in (ROOT/row["trace_file"]).read_text().splitlines():
            event=json.loads(line); item=event.get("item",{})
            if event.get("type")=="item.completed" and item.get("type")=="agent_message": messages.append(str(item.get("text","")))
        text="\n".join(messages).lower()
        strategy.append({"trial_id":row["trial_id"],"observable_messages":messages,
            "explicit_structure_or_reconstruction_attempt":any(term in text for term in STRUCTURE_TERMS),
            "explicit_interleaving_hypothesis": "interleav" in text,
            "concrete_stride_or_residue_test":any(term in text for term in CONCRETE_STRIDE_TERMS),
            "semantic_success":row["semantic_success"],"audited_classification":updated["audited_classification"]})
    atomic_bytes(ROOT/"results/trials-audited.jsonl","".join(json.dumps(row,ensure_ascii=False)+"\n" for row in audited).encode())
    summary={"performed_after_primary_scores_froze":True,"primary_scores_changed":False,
        "corrections":[
            {"field":"classification","scope":"two scrambled controls selecting Rowan",
             "original":"neither_target","audited":"control_target_answer",
             "primary_control_target_selection_boolean_was_already_true":True,"gate_impact":"none"},
            {"field":"explicit_stride_testing","scope":"two traces mentioning interleaving without testing it",
             "original_automatic_count":2,"audited_concrete_test_count":0,"gate_impact":"none"}],
        "audited_classification_counts":dict(sorted(Counter(row["audited_classification"] for row in audited).items())),
        "explicit_structure_or_reconstruction_attempts":sum(row["explicit_structure_or_reconstruction_attempt"] for row in strategy),
        "explicit_interleaving_hypotheses":sum(row["explicit_interleaving_hypothesis"] for row in strategy),
        "concrete_stride_or_residue_tests":sum(row["concrete_stride_or_residue_test"] for row in strategy),
        "strategy_records":strategy}
    atomic_json(ROOT/"results/audit-corrections.json",summary)
    by={(row["topic"],row["condition"]):row for row in audited}
    lines=["# Experiment 4C.2 audited result","",
        "This post-freeze audit corrects two presentation labels. It does not change response text, semantic-success booleans, control-selection booleans, or the preregistered stop decision.","",
        "## Answer identity","","| Topic | Hidden A | Hidden B | Scrambled | Complete pair |","| --- | --- | --- | --- | ---: |"]
    def label(row):
        if row["semantic_success"]: return f"{row['selected_target']} (expected)"
        if row["selected_target"]: return f"{row['selected_target']} ({row['audited_classification'].replace('_',' ')})"
        return row["audited_classification"].replace("_"," ")
    for topic in ("harbor","ceramics","garden"):
        a,b,c=by[(topic,"hidden_a")],by[(topic,"hidden_b")],by[(topic,"scrambled")]
        lines.append(f"| {topic} | {label(a)} | {label(b)} | {label(c)} | {'yes' if a['semantic_success'] and b['semantic_success'] else 'no'} |")
    lines += ["","## Outcome","","- Expected hidden answers: 1/6.","- Complete A/B pairs: 0/3.",
        "- Scrambled target selections: 2/3, both Rowan.","- Counterpart errors: 1, also Rowan.",
        "- Preregistered outcome: control contamination; 25% not authorized.","",
        "The single expected answer cannot be interpreted as ordered-stream recovery: all three harbor conditions selected Rowan, including Hidden B (where Mira was expected) and scrambled. The pattern is a Rowan/foreground-reconstruction bias.","",
        "## Observable trace strategy","",
        f"- Structural or reconstruction attempts: {summary['explicit_structure_or_reconstruction_attempts']}/9.",
        f"- Interleaving hypotheses: {summary['explicit_interleaving_hypotheses']}/9.",
        f"- Concrete stride/residue tests: {summary['concrete_stride_or_residue_tests']}/9.",
        "- Observable tool invocations: 0/9.","",
        "No claim is made about private chain of thought."]
    atomic_bytes(ROOT/"results/analysis-audited.md",("\n".join(lines)+"\n").encode())
    print(json.dumps({k:v for k,v in summary.items() if k!="strategy_records"},indent=2))


if __name__ == "__main__": main()

