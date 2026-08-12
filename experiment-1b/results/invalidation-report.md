# Experiment 1B same-host invalidation report

## Decision

The completed 320-trial Experiment 1A-R/1B dataset is invalidated for
confirmatory inference. It remains preserved byte-for-byte where applicable
for forensic analysis and runner development. It must not be pooled with a
hardened rerun or presented as a clean replication/normalization experiment.

## Discovery chronology

The execution protocol embargoed trace inspection until every Experiment
1A-R and 1B subject had completed. After sealing all 320 records, the raw JSONL
trace review revealed agents invoking shell commands against absolute host
paths. The finding occurred before the Experiment 1B freeze tag and before any
Experiment 2 subject was run.

## Scope

`leakage_trace_audit.py` mechanically audits completed command events without
rewriting traces. The final audit found:

```text
trials audited: 320
probe/access indicators: 28
host-access evidence: 14
direct clean-experiment leakage: 8
answer-key output: 5
```

Direct-leakage trial IDs:

```text
q0032 q0074 q0078 q0080 q0116 q0194 q0233 q0272
```

The sources included:

- historical `/tmp/q781*` prompts, metadata, and results;
- the current `word-salad` repository;
- persistent prior Codex session JSONL containing the handoff, clean payload,
  and answer key;
- unrelated prior-session context, demonstrating that `--ephemeral` prevented
  new persistence but did not make old session storage unreadable.

## Why row exclusion is insufficient

Only some agents chose to search the host, and that choice correlates with
task difficulty, tool use, lane count, and observable strategy. Excluding the
known contaminated rows would therefore introduce post-treatment selection
and would not address unobserved host-derived information. The opportunity to
read host state was shared by all subjects.

## Preserved analyses

The behavioral, effort, and strategy analyses remain in this directory as
descriptions of the invalidated run. They are useful for identifying failure
modes and sizing a rerun, not for testing the scientific hypothesis.

## Required remediation

A valid rerun must place the entire subject process behind an external
filesystem boundary. The subject environment should contain only:

- the Codex runtime and required shared libraries;
- minimal authentication/model metadata needed for inference;
- a fresh empty neutral working directory;
- the stimulus through stdin;
- no host repository mount, prior-session mount, historical `/tmp`, or answer
  key.

Before spending the rerun slate, adversarial probes must mechanically fail to
read sentinel files placed in each prohibited host location while a normal
GPT-5.6-Sol-xhigh invocation still succeeds.
