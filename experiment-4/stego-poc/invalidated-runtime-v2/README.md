# Invalidated runtime v2

The first fresh isolation audit found that the derivative image contained a
deny wrapper but Codex invoked `/bin/sh` directly rather than that wrapper. The
probe therefore executed successfully. No experimental development or held-out
subject was run. The failed audit and the original pre-inference stimulus freeze
are preserved here. Runtime v3 replaces `/bin/sh` itself with the deny wrapper;
the prompt corpus is unchanged and is re-frozen against the new image.
