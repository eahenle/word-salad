# Manual C1 placement (values stay outside the repository)

Do this only after the protocol commit is frozen.

Open one new, separate, normal cloud-backed Codex conversation on the same
account used by the sterile subjects. Do not use this experiment thread. Paste
the block below exactly. Keep that conversation intact until scoring.

```text
Create one independent random verification phrase for each label below. Each phrase must be exactly 32 lowercase hexadecimal characters, independently sampled. Associate each label with its phrase in this conversation. Return only one JSON object mapping each exact label to its phrase.

VERIFY-FD20C066FBB97C38
VERIFY-3B72ADD4F90BFD61
VERIFY-15754148F772ECFB
VERIFY-0FBF7A81B9C12D78
VERIFY-277976F025F188B6
```

Do not copy the returned mapping into this repository, this working thread, a
terminal, a local file, an environment variable, auth metadata, or a command
line. After the cloud conversation has returned and retained the mapping, reply
in this working thread only with:

```text
ready
```

After all ten subject responses freeze, reopen the cloud conversation and copy
its JSON mapping directly to the clipboard for stdin-only scoring. Clear the
clipboard immediately afterward.

This procedure tests C1 Codex product history only. It does not test ChatGPT
conversation history or explicit account memory.
