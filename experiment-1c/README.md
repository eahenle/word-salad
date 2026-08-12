# Experiment 1C: hardened replacement for Experiment 1A-R/1B

Experiment 1C is a clean replacement for the invalidated same-host run in
`../experiment-1b/`. It repeats the exact 320-trial prompt slate behind an
external container boundary. The invalidated dataset remains immutable at tag
`experiment-1b-invalidated-same-host` and is never pooled with these results.

## Fixed stimulus slate

The generator, normalization, scoring, and analysis code is versioned in
`../experiment-1b/`. Experiment 1C reuses the exact source-index geometry,
surface transformations, neutral IDs, and prompt hashes:

- variants: `original`, `lower`, `nopunct`, `lower_nopunct`;
- conditions: signal and all shuffled;
- lane counts: 1, 2, 4, 8;
- seeds: 1 through 10;
- model: `gpt-5.6-sol`;
- reasoning: `xhigh`;
- fresh ephemeral subject per trial.

`original` prompts must remain byte-identical to the frozen historical
Experiment 1 prompts. Normalized prompts reuse the same index permutations and
phases. The same mechanical invariants from Experiment 1B apply.

## Hardened subject boundary

The pinned subject image is:

```text
sha256:883e4d8d659d28c25d2473c0dec9ff43d1bafb7ce3920ada270627df3c202402
```

Each trial receives a new container with a read-only image and new tmpfs mounts
for `/subject`, `/tmp`, and `/codex-home`. No host repository, prior Codex
session, host temporary directory, experiment source, prompt file, metadata,
trace, or result is mounted. The prompt is supplied through stdin as the sole
user-level stimulus.

Codex needs repeated access to its credential during a turn, so the coordinator
runs as root inside the container and stores authentication in a root-only
`0700` tmpfs. Every model-generated shell path is a wrapper that permanently
drops to `uid=100(subject)`, clears effective capabilities, and applies
`NoNewPrivs=1` before interpreting the command. The adversarial preflight in
`results/isolation-validation.json` verifies that the command process cannot:

- see the host repository;
- see historical host `/tmp` artifacts;
- read the root-only credential file;
- read the root Codex process.

The preflight also verifies the dropped UID, zero effective capability mask,
and `NoNewPrivs=1` while a GPT-5.6-Sol-xhigh turn and shell call complete.

The container is an external sandbox, so Codex is invoked in its documented
external-sandbox automation mode. Nested Linux namespace sandboxing is disabled
because Docker Desktop does not permit the CLI's inner `bwrap` namespace. Shell
snapshots are disabled to avoid a root-to-unprivileged setup artifact; the shell
tool itself remains available.

Network access is required for inference. The image includes Cisco Secure
Access's public self-signed root CA because this host's egress network re-signs
TLS. Its SHA-256 fingerprint is:

```text
5E:4B:0E:86:FC:DB:40:5D:15:5E:67:40:55:3B:56:DE:D9:C5:98:F9:BE:23:57:97:69:3A:B3:02:2E:26:82:82
```

Same-host container isolation is materially stronger than a neutral working
directory but is not a cryptographic multi-host isolation guarantee.

## Execution

Generate and validate all exact prompts:

```bash
python3 -B experiment-1b/generate.py \
  --root experiment-1c --payload experiment-1c/payload.txt
python3 -B experiment-1b/validate.py \
  --root experiment-1c --payload experiment-1c/payload.txt
```

Run Phase I (`original`) first:

```bash
python3 -B experiment-1b/run_experiment.py \
  --root experiment-1c --payload experiment-1c/payload.txt \
  --runtime container \
  --image sha256:883e4d8d659d28c25d2473c0dec9ff43d1bafb7ce3920ada270627df3c202402 \
  --auth AUTH_JSON \
  --isolation-validation experiment-1c/results/isolation-validation.json \
  --variants original --workers 4 --timeout 900
```

Only after Phase I is complete, run the three normalization variants. Inspect
raw traces only after all 320 subjects finish.

Timeouts are subject outcomes and are not retried. Controller or transport
failures such as broken pipes, TLS disconnects, Docker daemon interruption, or
a missing turn caused by the runner are audited separately. Affected examples
are rerun individually with a fresh subject, while the failed attempt remains
preserved in an invalidated-attempt archive.

The audit-only retry selector is:

```bash
python3 -B experiment-1b/archive_infrastructure_failures.py \
  --root experiment-1c
```

Only `runner_exception`, `nonzero_exit`, and `missing_final_agent_message` are
eligible. Applying the archival step moves all four original artifacts and a
hash-bearing decision record under `invalidated-attempts/qNNNN/attempt-K/`.
The trial can then be named explicitly with the runner's `--trial-ids` option.
No correctness, response text, or trace strategy is used in that decision.

## Artifact separation

All prompts, indexed metadata, attempts, completions, raw stdout JSONL traces,
stderr streams, manifests, scores, audits, analyses, and figures live under
this directory. Nothing under the frozen historical experiment or the tagged
invalidated run is overwritten.
