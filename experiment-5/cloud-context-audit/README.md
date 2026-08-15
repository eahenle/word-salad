# Cloud-mediated context audit

This preregistered audit asks whether a fresh, locally sterile Codex subject can
return a random 128-bit label/value association that was placed only in a
separate cloud-backed product interaction. It precedes any further
interpretation of experiment-aware language in prior traces.

The audit uses five C1 Codex-history labels and five matched labels with no
model-accessible association. Every query runs in a fresh container using the
same audited no-tool image and model configuration as Experiment 4C:

- image: `sha256:e04e78a7926fc489536fe595073b58888238bc4107a6fd5281047432031627da`
- model: `gpt-5.6-sol`
- reasoning: `medium`
- no shell, filesystem tools, MCP, browser, apps, plugins, or repository mount
- ephemeral Codex thread and fresh container for every query

## Status and stopping rule

The Experiment 4 density program is paused. In particular, no 25% Rowan/Mira
stage may run. This audit is complete only after all ten responses freeze and a
human supplies the five expected values through standard input for exact
scoring.

Exact recovery of even one high-entropy value is a positive leakage finding and
suspends mechanistic interpretation of prior Codex results. No exact recovery,
with all controls returning `UNKNOWN`, substantially weakens this specific
cloud-history hypothesis but does not prove that every backend influence is
absent.

## Secret handling

The repository contains public labels, allocation, prompt text, code, hashes,
and redacted outcome categories. It must never contain an expected canary
value. See [IMPORTANT-NO-SECRET-VALUES-IN-GIT.md](IMPORTANT-NO-SECRET-VALUES-IN-GIT.md).

Raw traces, stderr, completed records, and responses are written beneath the
Git-ignored `private/` directory because a successful trace necessarily
contains the recovered value. They are frozen by SHA-256 in public results.

## Procedure

1. Run `python3 freeze_protocol.py` and commit the protocol before placement.
2. In a separate normal cloud-backed Codex conversation, follow
   `CLOUD-PLACEMENT-INSTRUCTIONS.md`. Do not paste the values into this thread,
   a terminal, a file, or the repository. Reply here only with `ready`.
3. Validate the exact subject boundary with
   `python3 validate_isolation.py --docker docker`.
4. Run all queries with an auth file path that contains no canary data:

   ```text
   python3 run.py --auth /path/to/auth.json --workers 1
   ```

5. Do not inspect responses until `results/execution-freeze.json` exists.
6. Reopen the separate cloud conversation, copy only its JSON mapping to the
   clipboard, and score without a command-line secret:

   ```text
   pbpaste | python3 score_after_unblinding.py
   ```

7. Clear the clipboard. The scorer never writes or prints expected values.

Only C1 is scheduled here. ChatGPT-history and explicit account-memory classes
remain separate possible follow-ups; they must not be silently pooled with C1.

## Provenance

Frozen Experiment 4 parent: `e81926adc710a7630e8b7c92c1ff71b6433930bc` (`experiment-4c2-density-125-control-stop`).
The local-image audit found no observable project context; see
`experiment-4/context-audit/conclusion.md`.
