FROM node:18-alpine

ARG CODEX_VERSION=0.147.0

COPY cisco-secure-access-root.crt /usr/local/share/ca-certificates/cisco-secure-access-root.crt
COPY subject-shell.sh /usr/local/libexec/subject-shell

RUN apk add --no-cache \
        bash \
        ca-certificates \
        coreutils \
        findutils \
        inotify-tools \
        python3 \
        ripgrep \
        util-linux \
    && update-ca-certificates \
    && npm install --global "@openai/codex@${CODEX_VERSION}" \
    && npm cache clean --force \
    && addgroup -S subject \
    && adduser -S -G subject -h /subject subject \
    && mkdir -p /subject /codex-home \
    && chown subject:subject /subject \
    && chown root:root /codex-home \
    && chmod 0700 /codex-home \
    && chmod 0755 /usr/local/libexec/subject-shell \
    && rm -f /bin/sh /bin/ash /bin/bash \
    && cp /usr/local/libexec/subject-shell /bin/sh \
    && ln /bin/sh /bin/ash \
    && ln /bin/sh /bin/bash \
    && sed -i 's#^root:\([^:]*:\)0:0:\([^:]*:\)[^:]*:[^:]*$#root:\10:0:\2/subject:/bin/sh#' /etc/passwd

COPY --chmod=0755 credential-gate.sh /usr/local/bin/credential-gate

USER root
WORKDIR /subject

ENV HOME=/subject \
    CODEX_HOME=/codex-home \
    SHELL=/bin/sh

ENTRYPOINT ["credential-gate"]
