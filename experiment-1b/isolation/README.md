# Hardened subject container

This image runs the subject-side Codex CLI inside a Linux filesystem that has
no host repository, host `/tmp`, or persistent Codex-session mount. The host
passes a length-prefixed authentication frame before the prompt on container
stdin. `credential-gate.sh` consumes exactly that frame into a private tmpfs
payload, leaving only the experimental stimulus on the stdin inherited by
Codex. Codex runs as root solely to traverse its private `0700` authentication
tmpfs. Every shell path the CLI can select (`sh`, `ash`, or `bash`) is replaced
by `subject-shell`, which drops to the unprivileged `subject` UID, clears all
capabilities, and sets `no_new_privs` before interpreting the model's command.
The subject therefore cannot traverse `/codex-home` or inspect the root Codex
process. No credential is placed in the environment, image, command line,
trace, or persistent volume.

The container uses a read-only root filesystem and fresh tmpfs mounts for
`/subject`, `/tmp`, and `/codex-home`; no named or persistent volume is reused
between subjects. `/subject` is an empty `root:subject` group-writable tmpfs so
both the coordinator and dropped-privilege command process can enter it. Common
command-line tools, including Python and ripgrep, are
installed so that agentic behavior is not suppressed merely by using a smaller
base image.

Build with the CLI version recorded by the protocol:

```bash
docker build \
  --build-arg CODEX_VERSION=0.147.0 \
  --tag word-salad-subject:codex-0.147.0 \
  experiment-1b/isolation
```

The runner adds:

```text
--read-only
--tmpfs /subject
--tmpfs /tmp
--tmpfs /codex-home
--cap-drop ALL
--cap-add SETUID
--cap-add SETGID
--security-opt no-new-privileges
--user root
```

The CLI is invoked with `--dangerously-bypass-approvals-and-sandbox` because
its nested Linux `bwrap` sandbox cannot create a user namespace inside Docker
Desktop's already restricted container. This is the CLI's explicit mode for an
externally sandboxed environment. It does not bypass the container or the
privilege-dropping shell wrapper.

Network access remains enabled because inference requires it. Before any
experimental rerun, `validate_isolation.py` sends an adversarial nonexperimental
probe and requires all host sentinel reads to fail while a normal model turn
still completes.

This host's egress network re-signs TLS with Cisco Secure Access. The image
therefore installs Cisco's public self-signed root CA certificate retrieved from
the AIA URL embedded in that chain;
its SHA-256 fingerprint and the final image digest are recorded in the clean-run
manifest. No private key or authentication material is included.
