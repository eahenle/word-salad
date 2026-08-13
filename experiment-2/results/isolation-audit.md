# Experiment 2 isolation and leakage audit

The complete 320-trial Codex-agent slate was scored and trace-audited only
after all subjects, including nine exact quota-failure reruns, had finished.
The raw traces show no observed access to the host repository, historical
trials, prior subjects, experiment documentation, prompt metadata, or
coordinator-side answer keys.

## Findings

- 22/320 subjects issued an environment or process probe.
- 0/320 traces contain observable host-access evidence.
- 0/320 traces contain direct experiment-context leakage.
- 20/320 traces printed a coherent reconstruction of the payload in shell
  output. Provenance shows these strings were derived from the supplied
  stimulus, not read from a host artifact.
- Nine first attempts were rejected before subject inference by an account
  usage cap. They were archived byte-for-byte and their exact prompts were
  rerun after a separate capacity probe succeeded. Prompt hashes match.

The mechanical reports are `integrity-audit.json`,
`leakage-trace-audit-summary.json`, and `leakage-trace-audit.jsonl`.

## Boundary

This is evidence about the observable same-host Docker boundary, not a
cryptographic proof of isolation. No host filesystem was mounted. Subject
commands ran as the unprivileged `subject` user with no effective capabilities
and `NoNewPrivs=1`; the Codex coordinator and credential tmpfs remained
root-only. Network access required for model inference remained available.

## Subject-visible context and tooling

Each subject was a fresh `codex exec --ephemeral` process started with
`--ignore-user-config`, `--ignore-rules`, `--strict-config`, and the neutral
working directory `/subject`. Its sole user-level input was the generated
stimulus supplied over stdin. The container had no mount of the Git repository,
prompt directories, metadata, source code, answer keys, prior responses,
traces, or results. Trial IDs, lane counts, phases, conditions, filenames, and
seed data were retained by the coordinator and were not in the user message.

The subject retained the ordinary Codex system/developer context and its shell
tool. Model-generated commands ran through the unprivileged wrapper described
above and could access only fresh container-local tmpfs plus the inference
network. The root-owned credential and coordinator process were not readable by
those commands. No subject trace, stderr stream, or summary was inspected until
the full active slate—including exact quota reruns—was complete.

The full environment-variable set was not archived because it could contain
authentication material. The executed command, image digest, flags, runtime
versions, isolation preflight, and observable environment probes are preserved.
This is a reproducibility/security tradeoff and a limitation of the audit.
