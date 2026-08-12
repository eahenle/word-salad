#!/bin/busybox sh
# All model-generated commands pass through this wrapper. The Codex coordinator
# starts as root to read its private auth file; command execution permanently
# drops to the subject account before a command string is interpreted.
exec /usr/bin/setpriv \
    --reuid=subject \
    --regid=subject \
    --clear-groups \
    --no-new-privs \
    /bin/busybox ash "$@"
