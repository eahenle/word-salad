# Invalidated runtime v4 configuration

The first narrowed runtime configuration disabled Codex's code-mode host. That
also prevented the explicitly requested positive-control marker call: Codex
returned `DONE` without invoking the fixed MCP tool. No experimental prompt ran.

The active configuration re-enables only Codex's sandboxed tool dispatcher so
it can reach the fixed marker MCP server. The dispatcher has no Node.js,
filesystem, or network primitives of its own. Native shell, unified execution,
browser/computer tools, apps, plugins, and external facilities remain disabled,
with the image-level `/bin/sh` exit-126 wrapper retained as defense in depth.
