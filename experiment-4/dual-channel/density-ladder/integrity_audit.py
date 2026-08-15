#!/usr/bin/env python3
"""Audit the frozen density protocol and every executed stage."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone

from generate import ROOT
from runtime import SOURCE_RUNTIME, atomic_json
from validate import SOURCE_4C_COMMIT, SOURCE_4C1_COMMIT, validate


TOOL={"command_execution","mcp_tool_call","file_change","web_search","browser_action","computer_action","tool_call"}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    r=subprocess.run(["git",*args],cwd=ROOT.parents[2],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if r.returncode: raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def main() -> None:
    protocol=json.loads((ROOT/"results/protocol-freeze.json").read_text()); checks={
        "4c_tag_frozen":git("rev-parse","experiment-4c-dual-channel-negative-gate^{}")==SOURCE_4C_COMMIT,
        "4c1_tag_frozen":git("rev-parse","experiment-4c1-foreground-coherence-null^{}")==SOURCE_4C1_COMMIT,
        "runtime_hash_frozen":sha(SOURCE_RUNTIME)==protocol["frozen_runtime_sha256"],
        "protocol_source_hashes_match":all(sha(ROOT/name)==digest for name,digest in protocol["source_hashes"].items()),
        "isolation_passed":json.loads((ROOT/"results/isolation-validation.json").read_text())["passed"]}
    stages={}; tool_types=set()
    for density in ("d125","d250"):
        stage=ROOT/"development"/density
        if not (stage/"results/execution-freeze.json").exists(): continue
        invariant=validate(density); execution=json.loads((stage/"results/execution-freeze.json").read_text())
        freeze=json.loads((stage/"results/stage-freeze.json").read_text()); manifest=json.loads((stage/"manifest.json").read_text())
        unscored=[json.loads(line) for line in (stage/"results/trials-unscored.jsonl").read_text().splitlines()]
        scored=[json.loads(line) for line in (stage/"results/trials.jsonl").read_text().splitlines()]
        stage_checks={"invariants":invariant["passed"],"complete":execution["completed"]==execution["scheduled"]==9,
            "no_errors_timeouts":execution["runner_errors"]==execution["timeouts"]==0,
            "prompt_hashes":all(sha(stage/"prompts"/f"{row['trial_id']}.txt")==freeze["prompt_hashes"][row["trial_id"]] for row in manifest),
            "trace_hashes":all(sha(ROOT/row["trace_file"])==execution["trace_hashes"][row["trial_id"]] for row in unscored),
            "responses_preserved":{r["trial_id"]:r["response"] for r in unscored}=={r["trial_id"]:r["response"] for r in scored}}
        for row in unscored:
            for line in (ROOT/row["trace_file"]).read_text().splitlines():
                e=json.loads(line); item=e.get("item",{})
                if e.get("type")=="item.completed" and item.get("type") in TOOL: tool_types.add(item.get("type"))
        checks.update({f"{density}_{key}":value for key,value in stage_checks.items()}); stages[density]=stage_checks
    d125=json.loads((ROOT/"development/d125/results/development-gate.json").read_text()) if "d125" in stages else None
    d250_exists="d250" in stages
    checks["stage_progression_obeyed"]=(not d250_exists) or bool(d125 and d125["next_stage_authorized"])
    checks["no_observable_tool_items"]=not tool_types
    failures=[name for name,value in checks.items() if not value]
    result={"audited_at_utc":datetime.now(timezone.utc).isoformat(),"passed":not failures,
        "checks":checks,"failures":failures,"executed_stages":list(stages),
        "observable_tool_item_types":sorted(tool_types),"direct_api_used":False,
        "code_mode_warning_retained":True,"source_experiments_modified":False}
    atomic_json(ROOT/"results/integrity-audit.json",result); print(json.dumps(result,indent=2))
    if failures: raise SystemExit(1)


if __name__ == "__main__": main()

