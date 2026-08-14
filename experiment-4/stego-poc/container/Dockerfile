FROM word-salad-subject:codex-0.147.0

COPY --chmod=700 marker_server.py /opt/q4/marker_server.py
COPY --chmod=700 credential-gate-q4 /usr/local/bin/credential-gate-q4
COPY --chmod=755 disabled-subject-shell /usr/local/libexec/subject-shell

# Codex command execution invokes /bin/sh directly. Replace that entrypoint only
# after all build-time shell operations. COPY performs the layer replacement
# without asking the currently executing shell to unlink itself. The credential
# gate uses BusyBox by absolute path and remains functional.
COPY --chmod=755 disabled-subject-shell /bin/sh

ENTRYPOINT ["credential-gate-q4"]
