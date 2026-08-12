#!/bin/busybox sh
# Consume a length-prefixed authentication frame before starting Codex. Codex
# runs as root only so it can read its private credential directory; every
# model-generated shell path is replaced by subject-shell and drops privileges.
set -eu

auth_file=/codex-home/auth.json

if ! IFS= read -r auth_length; then
    echo "credential gate requires a length-prefixed stdin frame" >&2
    exit 78
fi
case "$auth_length" in
    ''|*[!0-9]*)
        echo "credential gate received an invalid authentication length" >&2
        exit 78
        ;;
esac

umask 077
# Read exactly the framed credential bytes. The remaining stdin contains only
# the experimental stimulus and is inherited by Codex after exec.
dd if=/dev/stdin of="$auth_file" bs=1 count="$auth_length" iflag=fullblock status=none
if [ "$(stat -c %s "$auth_file")" != "$auth_length" ]; then
    echo "credential gate received a truncated authentication frame" >&2
    exit 78
fi
if ! python3 -c 'import json, sys; json.load(open(sys.argv[1], encoding="utf-8"))' "$auth_file"; then
    echo "credential gate received invalid authentication JSON" >&2
    exit 78
fi
chmod 600 "$auth_file"

# Codex must remain the foreground process so the experimental prompt supplied
# on stdin is not redirected to /dev/null by non-interactive shell job control.
exec codex "$@"
