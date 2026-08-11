# Experiment 1B leakage and isolation audit

## Subject-visible experimental input

The multiplexed stimulus is the sole user-level content. It is piped directly to `codex exec` stdin. The subject is not given an analysis request, decoding hint, filename, condition, surface variant, lane count, phase, seed, answer key, historical response, or trace.

## Process and working directory

- One fresh `codex exec --ephemeral` process is created per scheduled trial.
- Each process starts in its own newly created neutral `q.*` temporary directory.
- The directory contains no files.
- The sandbox is read-only and approvals are disabled.
- User config and user/project execution rules are ignored.
- The current directory is not a Git repository and `--skip-git-repo-check` is explicit.
- The temporary directory is deleted after the process exits.

## Environment

The Codex process inherits the coordinator process environment so the installed CLI retains its configured authentication/runtime access. Attempt records preserve only environment-variable names, never values. This means a subject that explicitly invokes a shell could observe inherited environment names and non-redacted values available to its process. No experiment answer key is placed in the environment until every subject in the scored slate has finished.

The runner records Python, platform, Codex CLI, model, reasoning effort, worker count, timeout, Git commit, generator/normalization versions, command template, payload hash, prompt hashes, and exact invocation arguments in machine-readable manifests.

## Files and state

- Prompt and metadata files use neutral `qNNNN` identifiers.
- Trace and stderr filenames are neutral.
- Subjects receive no path to this repository or its artifacts.
- No subject context is reused.
- No subject trace or response is inserted into another subject's prompt.
- Attempts are never implicitly retried.
- Scoring begins only after its corresponding subject slate completes.
- The coordinator-only answer key is not present in experiment source or configuration.

## Tool and context boundary

The Codex agent retains the ordinary tools made available by its default runtime, subject to a read-only sandbox and disabled approvals. Raw JSONL reveals observable tool calls and shell executions. The platform's private internal reasoning and hidden system/developer instructions are not exposed by `codex exec --json`; this experiment does not claim otherwise.

The exact default system/developer context is platform-managed and not fully enumerable from the emitted trace. `--ignore-user-config`, `--ignore-rules`, `--strict-config`, the empty working directory, and the ephemeral session reduce inherited customization.

## Residual risk

Same-host sandboxing is not cryptographic isolation. A subject that independently guesses absolute host paths could potentially discover readable repository content, generated prompts, metadata, or already completed neutral artifacts. Neutral naming and the lack of any supplied repository path reduce this risk but do not eliminate it. Stronger replication should use a separate container/account/filesystem image that contains only the single stimulus and runtime prerequisites.
