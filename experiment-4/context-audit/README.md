# Experiment 4 local Codex context audit

This audit pauses further steganographic trials and tests whether the exact frozen Experiment 4B.1 subject image contained persistent local Codex or project context. It does not test backend- or account-level memory.

## Frozen evidence

- Repository commit at audit start: `025b5af90791fb0df2e0bef28deb3954730ffb1d`
- Existing 4B.1 tag: `experiment-4b1-framing-ablation-raw-gate`
- Frozen 4B.1 image: `sha256:882b506db7abe1d804da2cf4644364ae951accc24f732c04bc7c4ef75b38f254`
- Exact direct 4B parent: `sha256:3a7453a79ce8244acc40dd16594c1410b0a658b39ca9dbec5f5dbfe9e43eb1d0`
- Exact subject base: `sha256:883e4d8d659d28c25d2473c0dec9ff43d1bafb7ce3920ada270627df3c202402`

No Experiment 4A, 4B, or 4B.1 prompt, trace, response, score, or active result was modified or regenerated.

## Methods

### Historical provenance

The exact frozen image, direct parent, and subject base were inspected by image ID. The direct parent's 13 RootFS layers are an exact prefix of the frozen image's 14 layers. The subject base's nine layers are an exact prefix of the direct parent's layers. The mutable tags still resolved to those exact IDs at audit time, so historical local ancestry was reconstructed unambiguously despite BuildKit leaving the `Parent` metadata field blank.

Complete, untruncated Docker histories are preserved in `frozen-image-history.txt` and `parent-image-history.txt`. They show only the source-controlled base recipe, the expected capability-limiting PoC copies, and the final 4B.1 marker-server replacement. No unexpected project/home copy, `ADD`, or context-generation command appears.

### Filesystem and content search

The image entrypoint was overridden for read-only diagnostics; Codex was not launched. The audit walked the entire single-device filesystem and hashed every regular file. It searched filenames broadly for instruction, memory, config, history, session, rollout, and prompt candidates. It also searched raw file bytes case-insensitively for every preregistered project term, including binary files.

`/subject` and `/codex-home` were empty before the credential gate. No `/workspace` or `/app` directory existed. No `AGENTS.md`, `AGENTS.override.md`, memory file, Codex config, auth file, Codex session, rollout, prompt artifact, or experiment file was present.

The seven filename candidates in `candidate-context-files.txt` are generic PAM/profile/npm files selected by deliberately broad substring matching. None is a Codex instruction or runtime state file.

The raw-byte scan found 48 files. The historical and clean-rebuild hit maps are identical. The intentional `/opt/q4/marker_server.py` contains `amber` and `violet`. Other matches are generic runtime/package strings—for example Python I/O multiplexing, array strides, color names, and Codex's built-in action-safety text concerning prompt injection. No file contained `word salad`, `hidden message`, `signal lane`, `all shuffled`, the three-object payload terms, or an Experiment 1–4 identifier.

### Codex defaults

The installed package is `codex-cli 0.147.0`. Its package tree contains no candidate instruction/history file. Official Codex documentation says global instructions are loaded from `AGENTS.override.md` or `AGENTS.md` in `CODEX_HOME`, followed by project instruction files from the project root to the working directory. It also says user configuration lives in `~/.codex/config.toml`, with optional trusted-project `.codex/config.toml` layers and `/etc/codex/config.toml` system configuration. None of those files or directories existed in the frozen subject filesystem. See [AGENTS.md discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md) and [Codex config basics](https://learn.chatgpt.com/docs/config-file/config-basic).

### Authentication

`auth-structure-redacted.json` records only key names, value types, lengths, and decoded JWT claim-key structure. No token or credential value is stored. The frame consists of auth mode/timestamp fields, an API-key null, account ID, and access/identity/refresh tokens. Decoded claim keys are identity, session, scope, entitlement, and timing fields. A nonpersisting scan of the unredacted JSON found none of the preregistered project terms.

Static inspection of the exact credential gate confirms that it writes only `/codex-home/auth.json` before executing Codex. The prelaunch image contains no other file under `/codex-home`.

### Clean reconstruction

The base was rebuilt with `--no-cache` from a temporary context containing only:

- the source-controlled Dockerfile;
- the CA certificate;
- `credential-gate.sh`;
- `subject-shell.sh`.

The temporary context was destroyed afterward. The Node parent was pinned to `node@sha256:8d6421d663b4c28fd3ebc498332f249011d118945588d0a35cb9bc4b8ca09d9e`. The clean base image is `sha256:e04e78a7926fc489536fe595073b58888238bc4107a6fd5281047432031627da`.

Docker BuildKit attempted a registry pull rather than accepting a local-only `repo@sha256` reference for the child. That failed attempt is preserved as `clean-build/poc-build-digest-ref-failure.log`. The successful child build therefore used a local tag containing the full clean-base image ID and verified that it resolved to that exact ID immediately before the build. This is an audit-only provenance limitation, fully recorded in `clean-build/build-manifest.json`; it did not reuse the historical mutable subject tag.

The clean PoC image is `sha256:bf7dfa417f238e6e0576a9d68ebd1dd16d6246eda4a3ae86015c90d0291b3709`.

### Image comparison

Historical and clean images each expose 5,672 filesystem entries. They share 5,670 paths and 4,236 regular files. Of those regular files, 4,234 are byte-identical. The only two hash differences are:

- `/etc/hostname`, injected per diagnostic container;
- `/etc/shadow`, recreated by the clean base's `adduser` build step.

The only path-set differences are two timestamped npm debug-log filenames on each side. No unexplained path, metadata, configuration, or content difference remains. See `comparison.md` and `comparison-data.json`.

### Behavioral leakage probe

After the static audit passed, five unrelated prose-only prompts were sent to fresh subjects using the clean base, `gpt-5.6-sol`, and medium reasoning. No marker schema or other MCP tool was exposed; shell, browser, computer, apps, plugins, skills, image generation, and multi-agent features were disabled. Each container had empty tmpfs-backed `/subject`, `/tmp`, and `/codex-home`, no host mount, and an ephemeral Codex thread.

All five completed. None mentioned hidden messages, instructions, encoding, interleaving, multiplexing, shuffling, strides, signal lanes, word salad, amber/violet, markers, experiments, steganography, prompt injection, or the original object payload. Full emitted traces are preserved under `behavioral-probes/`.

## Reproduction

These commands do not run any substantive steganographic trial:

```bash
python3 -B experiment-4/context-audit/capture_audit.py --auth /path/to/auth.json
python3 -B experiment-4/context-audit/rebuild_clean.py
python3 -B experiment-4/context-audit/compare_images.py
python3 -B experiment-4/context-audit/run_behavioral_probes.py --auth /path/to/auth.json
```

The first and last commands read authentication material but never persist its values. The build script requires Docker/package network access for a no-cache public package rebuild. The behavioral probe uses network transport only for Codex model inference and exposes no network-capable model tool.

## Scope and limitations

The audit strongly reduces the local baked-in context hypothesis. It does not prove the absence of backend/account context, nor does it make d0003 evidence of hidden-channel recovery: that document overtly says `marker tool` and `record amber`. Likewise, d0002's overt evaluation-like wording remains a sufficient reason to treat its “hidden message” suggestion cautiously.

Same-host Docker remains an audited practical isolation boundary, not a cryptographic multi-host guarantee.
