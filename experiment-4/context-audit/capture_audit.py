#!/usr/bin/env python3
"""Capture a read-only provenance and filesystem audit of the frozen 4B.1 image.

The script never launches Codex. It overrides the image entrypoint with Python
or the Codex binary for static inventory/version checks, and it redacts every
authentication value while retaining JSON key/type structure.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
FROZEN = "sha256:882b506db7abe1d804da2cf4644364ae951accc24f732c04bc7c4ef75b38f254"
DIRECT_PARENT = "sha256:3a7453a79ce8244acc40dd16594c1410b0a658b39ca9dbec5f5dbfe9e43eb1d0"
BASE = "sha256:883e4d8d659d28c25d2473c0dec9ff43d1bafb7ce3920ada270627df3c202402"
DIRECT_PARENT_TAG = "word-salad-canary:codex-0.147.0-v5"
BASE_TAG = "word-salad-subject:codex-0.147.0"

TERMS = (
    "word salad", "hidden message", "multiplex", "interleave", "interleaved",
    "shuffled", "stride", "signal lane", "all shuffled", "amber", "violet",
    "brass key", "silver coin", "glass marble", "experiment 1", "experiment 2",
    "experiment 3", "experiment 4", "stego", "prompt injection",
)


def run(args: list[str], *, timeout: int = 300, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=timeout, check=False)
    if check and result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {args!r}\n"
            f"{result.stderr.decode(errors='replace')}"
        )
    return result


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_json(path: Path, value: Any) -> None:
    write_bytes(path, (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode())


def inspect(image: str) -> dict[str, Any]:
    return json.loads(run(["docker", "image", "inspect", image]).stdout)[0]


def history(image: str) -> bytes:
    return run(["docker", "image", "history", "--no-trunc", image]).stdout


def rootfs_prefix(ancestor: dict[str, Any], descendant: dict[str, Any]) -> bool:
    a = ancestor["RootFS"]["Layers"]
    b = descendant["RootFS"]["Layers"]
    return b[:len(a)] == a


INVENTORY_PROGRAM = r'''
import hashlib, json, os, stat
skip = {"/proc", "/sys", "/dev"}
for root, dirs, files in os.walk("/", topdown=True, followlinks=False):
    dirs[:] = sorted(d for d in dirs if os.path.join(root, d) not in skip)
    names = sorted(dirs + files)
    for name in names:
        path = os.path.join(root, name)
        try:
            info = os.lstat(path)
        except OSError as exc:
            print(json.dumps({"path": path, "error": type(exc).__name__}, sort_keys=True))
            continue
        mode = info.st_mode
        if stat.S_ISREG(mode): kind = "file"
        elif stat.S_ISDIR(mode): kind = "dir"
        elif stat.S_ISLNK(mode): kind = "symlink"
        elif stat.S_ISCHR(mode): kind = "char"
        elif stat.S_ISBLK(mode): kind = "block"
        elif stat.S_ISFIFO(mode): kind = "fifo"
        elif stat.S_ISSOCK(mode): kind = "socket"
        else: kind = "other"
        row = {"path": path, "kind": kind, "mode": oct(stat.S_IMODE(mode)),
               "uid": info.st_uid, "gid": info.st_gid, "size": info.st_size}
        if kind == "file":
            try:
                digest = hashlib.sha256()
                with open(path, "rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                row["sha256"] = digest.hexdigest()
            except OSError as exc:
                row["hash_error"] = type(exc).__name__
        if kind == "symlink":
            try: row["target"] = os.readlink(path)
            except OSError as exc: row["target_error"] = type(exc).__name__
        print(json.dumps(row, sort_keys=True, ensure_ascii=True))
'''


SEARCH_PROGRAM = r'''
import hashlib, json, os, re, stat
terms = json.loads(os.environ["AUDIT_TERMS"])
patterns = [(term, re.compile(re.escape(term.encode()), re.I)) for term in terms]
skip = {"/proc", "/sys", "/dev"}
for root, dirs, files in os.walk("/", topdown=True, followlinks=False):
    dirs[:] = sorted(d for d in dirs if os.path.join(root, d) not in skip)
    for name in sorted(files):
        path = os.path.join(root, name)
        try:
            if not stat.S_ISREG(os.lstat(path).st_mode): continue
            with open(path, "rb") as handle: data = handle.read()
        except (OSError, MemoryError):
            continue
        matched = []
        contexts = []
        for term, pattern in patterns:
            found = list(pattern.finditer(data))
            if not found: continue
            matched.append(term)
            for item in found[:10]:
                before = data.rfind(b"\n", 0, item.start()) + 1
                after = data.find(b"\n", item.end())
                if after < 0: after = min(len(data), item.end() + 120)
                snippet = data[before:after][:400]
                contexts.append({"term": term, "offset": item.start(),
                    "context": snippet.decode("utf-8", errors="backslashreplace")})
        if matched:
            print(json.dumps({"path": path, "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data), "matched_terms": matched, "contexts": contexts},
                sort_keys=True, ensure_ascii=True))
'''


PRELAUNCH_PROGRAM = r'''
import json, os, stat
sensitive = re = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "AUTH", "KEY")
print("PWD=" + os.getcwd())
print("HOME=" + str(os.environ.get("HOME")))
print("CODEX_HOME=" + str(os.environ.get("CODEX_HOME")))
print("ENVIRONMENT:")
for key in sorted(os.environ):
    value = "<redacted>" if any(piece in key.upper() for piece in sensitive) else os.environ[key]
    print(f"{key}={value}")
for base in ("/subject", "/codex-home", "/root", "/home", "/workspace", "/app", "/opt", "/tmp"):
    print(f"TREE {base}:")
    if not os.path.lexists(base):
        print("  <absent>")
        continue
    for root, dirs, files in os.walk(base, topdown=True, followlinks=False):
        dirs.sort(); files.sort()
        print(root + "/")
        for name in files:
            path = os.path.join(root, name)
            try:
                info = os.lstat(path)
                print(f"  {oct(stat.S_IMODE(info.st_mode))} {info.st_size} {path}")
            except OSError as exc:
                print(f"  <{type(exc).__name__}> {path}")
'''


def docker_python(image: str, program: str, *, env: dict[str, str] | None = None,
                  timeout: int = 600) -> bytes:
    command = ["docker", "run", "--rm", "--network", "none", "--read-only"]
    for key, value in sorted((env or {}).items()):
        command += ["--env", f"{key}={value}"]
    command += ["--entrypoint", "python3", image, "-c", program]
    return run(command, timeout=timeout).stdout


def layer_for(path: str) -> str:
    if path == "/opt/q4/marker_server.py":
        return "frozen 4B.1 top COPY layer (73aded3e...)"
    if path in {"/usr/local/bin/credential-gate-q4", "/usr/local/libexec/subject-shell", "/bin/sh"}:
        return "direct 4B parent COPY layer (path-specific diff layer in parent history)"
    if path.startswith("/usr/local/lib/node_modules/@openai/") or path == "/usr/local/bin/codex":
        return "subject-base RUN layer containing npm install (5f70bf18...) or its symlink metadata"
    return "base/parent filesystem; exact path-to-layer attribution not established"


def render_search_hits(hits: list[dict[str, Any]], title: str) -> bytes:
    lines = [title, "", "Search was case-insensitive over raw bytes of every regular file.", ""]
    for row in hits:
        lines += [f"PATH: {row['path']}", f"SHA256: {row['sha256']}",
                  f"SIZE: {row['size']}", f"LAYER: {layer_for(row['path'])}",
                  f"TERMS: {', '.join(row['matched_terms'])}"]
        for context in row["contexts"]:
            safe = context["context"].encode("unicode_escape").decode("ascii").rstrip()
            lines.append(f"  {context['term']} @ {context['offset']}: {safe}")
        lines.append("")
    if not hits: lines.append("NO MATCHES")
    return ("\n".join(lines).rstrip() + "\n").encode()


def candidate_reason(path: str) -> list[str]:
    low_path = path.lower()
    base = Path(path).name.lower()
    reasons = []
    if base in {"agents.md", "agents.override.md", "memory.md"}: reasons.append("instruction/memory basename")
    if "instruction" in base: reasons.append("instruction-like basename")
    if any(piece in base for piece in ("history", "session", "rollout", "prompt")):
        reasons.append("history/session/rollout/prompt-like basename")
    if "/.codex/" in low_path or low_path.startswith("/codex-home/"):
        reasons.append("Codex home/config path")
    if base in {"config.toml", "requirements.toml", "auth.json"}:
        reasons.append("Codex-sensitive configuration basename")
    return reasons


def decoded_jwt_payload(value: str) -> Any | None:
    if value.count(".") != 2 or len(value) < 40:
        return None
    try:
        encoded = value.split(".", 2)[1]
        encoded += "=" * (-len(encoded) % 4)
        return json.loads(base64.urlsafe_b64decode(encoded))
    except Exception:
        return None


def redact_structure(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): redact_structure(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return {"type": "array", "length": len(value),
                "items": [redact_structure(item) for item in value[:10]]}
    if isinstance(value, str):
        payload = decoded_jwt_payload(value)
        row = {"type": "jwt" if payload is not None else "string",
               "redacted": True, "length": len(value)}
        if payload is not None:
            row["decoded_payload_structure"] = redact_structure(payload)
        return row
    if value is None: return {"type": "null"}
    if isinstance(value, bool): return {"type": "boolean", "redacted": True}
    if isinstance(value, int): return {"type": "integer", "redacted": True}
    if isinstance(value, float): return {"type": "number", "redacted": True}
    return {"type": type(value).__name__, "redacted": True}


def value_term_scan(value: Any) -> list[str]:
    rendered = json.dumps(value, ensure_ascii=False).lower()
    return [term for term in TERMS if term in rendered]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth", type=Path)
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)

    commit = run(["git", "rev-parse", "HEAD"]).stdout.decode().strip()
    write_json(ROOT / "audit-freeze.json", {
        "audit_started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repository_commit": commit,
        "frozen_image": FROZEN,
        "frozen_direct_parent": DIRECT_PARENT,
        "subject_base": BASE,
        "substantive_stego_trials_paused": True,
    })

    frozen = inspect(FROZEN)
    direct = inspect(DIRECT_PARENT)
    base = inspect(BASE)
    write_json(ROOT / "frozen-image-inspect.json", frozen)
    write_bytes(ROOT / "frozen-image-history.txt", history(FROZEN))
    tag_checks = {}
    for tag in (DIRECT_PARENT_TAG, BASE_TAG):
        check = run(["docker", "image", "inspect", tag], check=False)
        tag_checks[tag] = {
            "available": check.returncode == 0,
            "resolved_id": (json.loads(check.stdout)[0]["Id"] if check.returncode == 0 else None),
            "stderr": check.stderr.decode(errors="replace"),
        }
    write_json(ROOT / "parent-image-inspect.json", {
        "direct_parent": direct,
        "subject_base": base,
        "mutable_tag_checks_at_audit_time": tag_checks,
        "ancestry_checks": {
            "base_layers_are_exact_prefix_of_direct_parent": rootfs_prefix(base, direct),
            "direct_parent_layers_are_exact_prefix_of_frozen": rootfs_prefix(direct, frozen),
        },
        "note": "Docker's image Parent field is blank under BuildKit; exact RootFS prefix identity establishes local layer ancestry.",
    })
    parent_history = (
        f"DIRECT PARENT {DIRECT_PARENT} ({DIRECT_PARENT_TAG})\n".encode()
        + history(DIRECT_PARENT)
        + f"\nSUBJECT BASE {BASE} ({BASE_TAG})\n".encode()
        + history(BASE)
    )
    write_bytes(ROOT / "parent-image-history.txt", parent_history)

    inventory_raw = docker_python(FROZEN, INVENTORY_PROGRAM, timeout=1200)
    inventory_rows = [json.loads(line) for line in inventory_raw.splitlines()]
    rendered = ["kind\tmode\tuid\tgid\tsize\tsha256\tpath\ttarget"]
    for row in inventory_rows:
        rendered.append("\t".join("-" if row.get(key, "") in ("", None) else str(row[key]) for key in
                                  ("kind", "mode", "uid", "gid", "size", "sha256", "path", "target")))
    write_bytes(ROOT / "filesystem-inventory.txt", ("\n".join(rendered) + "\n").encode())

    candidates = []
    for row in inventory_rows:
        if row.get("kind") != "file": continue
        reasons = candidate_reason(row["path"])
        if reasons:
            candidates.append({"path": row["path"], "reasons": reasons,
                               "size": row.get("size"), "layer": layer_for(row["path"])})
    lines = ["# Candidate context-bearing files", "",
             "Generated from the complete frozen-image inventory. Presence is not itself evidence that Codex loads a file.", ""]
    for row in candidates:
        lines += [f"PATH: {row['path']}", f"REASON: {', '.join(row['reasons'])}",
                  f"SIZE: {row['size']}", f"LAYER: {row['layer']}", ""]
    write_bytes(ROOT / "candidate-context-files.txt", ("\n".join(lines).rstrip() + "\n").encode())

    search_raw = docker_python(FROZEN, SEARCH_PROGRAM,
                               env={"AUDIT_TERMS": json.dumps(TERMS)}, timeout=1200)
    hits = [json.loads(line) for line in search_raw.splitlines()]
    write_bytes(ROOT / "project-string-hits.txt",
                render_search_hits(hits, "# Frozen image project-string content search"))

    write_bytes(ROOT / "codex-home-prelaunch.txt", docker_python(FROZEN, PRELAUNCH_PROGRAM))
    version = run(["docker", "run", "--rm", "--network", "none", "--read-only",
                   "--entrypoint", "/usr/local/bin/codex", FROZEN, "--version"], timeout=60)
    package_rows = [row for row in inventory_rows
                    if row.get("path", "").startswith("/usr/local/lib/node_modules/@openai/")]
    write_json(ROOT / "codex-installation-audit.json", {
        "version_stdout": version.stdout.decode(errors="replace").strip(),
        "version_stderr": version.stderr.decode(errors="replace").strip(),
        "package_path_entries": len(package_rows),
        "candidate_package_context_files": [row for row in candidates
            if row["path"].startswith("/usr/local/lib/node_modules/@openai/")],
        "runtime_created_files_before_launch": [],
        "classification": {
            "static_package_files": "/usr/local/lib/node_modules/@openai/**",
            "runtime_state_directory": "/codex-home (empty in immutable image and before gate)",
            "project_working_directory": "/subject (empty in immutable image)",
        },
    })

    if args.auth:
        auth = json.loads(args.auth.read_text(encoding="utf-8"))
        write_json(ROOT / "auth-structure-redacted.json", {
            "source_path_not_persisted": True,
            "values_redacted": True,
            "structure": redact_structure(auth),
            "project_term_matches_in_unredacted_values": value_term_scan(auth),
            "assessment_scope": "JSON key names, value types, and lengths only; no credential value was persisted.",
        })
    else:
        write_json(ROOT / "auth-structure-redacted.json", {
            "not_captured": True,
            "reason": "Run again with --auth PATH; values will remain redacted.",
        })

    print(json.dumps({
        "commit": commit,
        "frozen_filesystem_entries": len(inventory_rows),
        "candidate_files": len(candidates),
        "project_string_hit_files": len(hits),
        "direct_parent_prefix": rootfs_prefix(direct, frozen),
        "base_prefix": rootfs_prefix(base, direct),
        "codex_version": version.stdout.decode(errors="replace").strip(),
    }, indent=2))


if __name__ == "__main__":
    main()
