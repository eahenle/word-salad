# Conclusion

## Finding

The frozen local image and clean rebuild contained no observable project-specific memory, `AGENTS.md` file, Codex history, Codex configuration, session/rollout artifact, prompt file, or experiment context.

The local baked-in context hypothesis is not supported by this audit.

Evidence:

- The exact frozen image's direct parent and subject base were recovered by image ID, and their RootFS layers are exact ancestry prefixes.
- Complete history contains no unexpected `COPY`, `ADD`, or context-generation step.
- `/subject` and `/codex-home` are empty before launch.
- Broad filename search returned only seven generic PAM/profile/npm candidates.
- Full raw-byte search returned no `word salad`, `hidden message`, object-payload, signal-lane, all-shuffled, or Experiment 1–4 content.
- Historical and clean-rebuild logical filesystems match, with only expected build/runtime differences.
- Authentication structure contains identity/session/scope fields but no project-term match; no values were persisted.
- Five fresh no-tool subjects given unrelated benign prose produced no experiment-related terminology.

## Effect on 4B.1

The audit does not validate d0003 as hidden-channel recovery. Its overt text directly says that crews use a `marker tool` and should `record amber`, so ordinary semantic transfer remains a decisive confound even in a clean image.

d0002's spontaneous offer to “analyze it for a hidden message” is unusual but not evidence of local leakage. Its visible prose is conspicuously evaluation-like: it names a marker tool, contrasts violet and amber, asks staff to record a label, and refers to a requested summary. With no observable local context and no analogous language in five unrelated probes, the overt document itself is the more economical explanation.

## Interpretation boundary

This audit substantially reduces one local contamination explanation. It cannot exclude every upstream or account-level influence, and it cannot distinguish hidden-subsequence recovery from overt semantic cues in the existing development covers.

No additional steganographic trial was run. Future interpretation should retain the contamination caveat as audited-and-not-observed, while treating overt marker language as the primary unresolved 4B.1 confound.
