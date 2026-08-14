#!/usr/bin/env python3
"""Rebuild the subject and capability-limited PoC images from clean contexts."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from capture_audit import (INVENTORY_PROGRAM, PRELAUNCH_PROGRAM, SEARCH_PROGRAM,
                           TERMS, candidate_reason, docker_python, inspect,
                           render_search_hits, run, write_bytes, write_json)


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CLEAN = HERE / "clean-build"
BASE_SOURCE = REPO / "experiment-1b/isolation"
POC_SOURCE = REPO / "experiment-4/stego-poc/container"
FRAMING_SOURCE = REPO / "experiment-4/stego-poc/framing-ablation/container"
BASE_TAG = "word-salad-subject-audit:codex-0.147.0-clean-v1"
POC_TAG = "word-salad-canary-audit:codex-0.147.0-clean-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_file(source: Path, destination: Path) -> dict:
    shutil.copy2(source, destination)
    return {"source": str(source.relative_to(REPO)), "destination": destination.name,
            "sha256": sha(destination), "size": destination.stat().st_size}


def build(context: Path, tag: str, log_path: Path) -> dict:
    command = ["docker", "build", "--no-cache", "--tag", tag, str(context)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=1800, check=False)
    write_bytes(log_path, result.stdout)
    if result.returncode:
        raise RuntimeError(f"clean Docker build failed ({result.returncode}); see {log_path}")
    data = inspect(tag)
    return {"command": command, "exit_status": result.returncode, "image_id": data["Id"],
            "repo_digests": data.get("RepoDigests", []), "created": data["Created"],
            "size": data["Size"]}


def pinned_local_ref(tag: str, data: dict) -> str:
    repository = tag.split(":", 1)[0]
    for item in data.get("RepoDigests", []):
        if item.startswith(repository + "@sha256:"):
            return item
    return repository + "@" + data["Id"]


def content_named_local_ref(image_id: str) -> str:
    """Create a local-only reference whose name embeds the verified image ID.

    BuildKit attempts a registry pull for local-only ``repo@sha256`` references.
    The derived tag is therefore used only after and while checking that it
    resolves to the exact expected immutable image ID.
    """
    reference = "word-salad-subject-audit:content-" + image_id.removeprefix("sha256:")
    run(["docker", "image", "tag", image_id, reference])
    if inspect(reference)["Id"] != image_id:
        raise RuntimeError("content-named local parent reference did not resolve to expected image ID")
    return reference


def inventory(image: str, path: Path) -> list[dict]:
    raw = docker_python(image, INVENTORY_PROGRAM, timeout=1200)
    rows = [json.loads(line) for line in raw.splitlines()]
    rendered = ["kind\tmode\tuid\tgid\tsize\tsha256\tpath\ttarget"]
    for row in rows:
        rendered.append("\t".join("-" if row.get(key, "") in ("", None) else str(row[key]) for key in
                                  ("kind", "mode", "uid", "gid", "size", "sha256", "path", "target")))
    write_bytes(path, ("\n".join(rendered) + "\n").encode())
    return rows


def search(image: str, path: Path) -> list[dict]:
    raw = docker_python(image, SEARCH_PROGRAM,
                        env={"AUDIT_TERMS": json.dumps(TERMS)}, timeout=1200)
    rows = [json.loads(line) for line in raw.splitlines()]
    write_bytes(path, render_search_hits(rows, "# Clean image project-string content search"))
    return rows


def main() -> None:
    CLEAN.mkdir(parents=True, exist_ok=True)
    node = inspect("node:18-alpine")
    node_ref = pinned_local_ref("node:18-alpine", node)
    source_dockerfile = (BASE_SOURCE / "Dockerfile").read_text()
    if not source_dockerfile.startswith("FROM node:18-alpine\n"):
        raise RuntimeError("unexpected subject-base Dockerfile FROM line")
    pinned_dockerfile = source_dockerfile.replace(
        "FROM node:18-alpine\n", f"FROM {node_ref}\n", 1)

    with tempfile.TemporaryDirectory(prefix="word-salad-context-audit-base-") as temp_name:
        context = Path(temp_name)
        (context / "Dockerfile").write_text(pinned_dockerfile)
        base_files = [
            {"source": "experiment-1b/isolation/Dockerfile", "destination": "Dockerfile",
             "source_sha256": sha(BASE_SOURCE / "Dockerfile"),
             "rendered_sha256": sha(context / "Dockerfile"),
             "change": f"FROM pinned from node:18-alpine to {node_ref}"},
            copy_file(BASE_SOURCE / "cisco-secure-access-root.crt", context / "cisco-secure-access-root.crt"),
            copy_file(BASE_SOURCE / "credential-gate.sh", context / "credential-gate.sh"),
            copy_file(BASE_SOURCE / "subject-shell.sh", context / "subject-shell.sh"),
        ]
        base_build = build(context, BASE_TAG, CLEAN / "base-build.log")

    base_image = inspect(base_build["image_id"])
    base_pinned = content_named_local_ref(base_build["image_id"])
    poc_source = (POC_SOURCE / "Dockerfile").read_text()
    if not poc_source.startswith("FROM word-salad-subject:codex-0.147.0\n"):
        raise RuntimeError("unexpected PoC Dockerfile FROM line")
    poc_dockerfile = poc_source.replace(
        "FROM word-salad-subject:codex-0.147.0\n", f"FROM {base_pinned}\n", 1)

    with tempfile.TemporaryDirectory(prefix="word-salad-context-audit-poc-") as temp_name:
        context = Path(temp_name)
        (context / "Dockerfile").write_text(poc_dockerfile)
        poc_files = [
            {"source": "experiment-4/stego-poc/container/Dockerfile", "destination": "Dockerfile",
             "source_sha256": sha(POC_SOURCE / "Dockerfile"),
             "rendered_sha256": sha(context / "Dockerfile"),
             "change": f"FROM pinned to clean base {base_pinned}"},
            copy_file(FRAMING_SOURCE / "marker_server.py", context / "marker_server.py"),
            copy_file(POC_SOURCE / "credential-gate-q4", context / "credential-gate-q4"),
            copy_file(POC_SOURCE / "disabled-subject-shell", context / "disabled-subject-shell"),
        ]
        if inspect(base_pinned)["Id"] != base_build["image_id"]:
            raise RuntimeError("clean parent reference changed immediately before child build")
        poc_build = build(context, POC_TAG, CLEAN / "poc-build.log")

    clean_image = inspect(poc_build["image_id"])
    write_json(CLEAN / "image-inspect.json", clean_image)
    write_bytes(CLEAN / "image-history.txt",
                run(["docker", "image", "history", "--no-trunc", poc_build["image_id"]]).stdout)
    rows = inventory(poc_build["image_id"], CLEAN / "filesystem-inventory.txt")
    hits = search(poc_build["image_id"], CLEAN / "project-string-hits.txt")
    write_bytes(CLEAN / "codex-home-prelaunch.txt",
                docker_python(poc_build["image_id"], PRELAUNCH_PROGRAM))
    candidates = []
    for row in rows:
        if row.get("kind") != "file": continue
        reasons = candidate_reason(row["path"])
        if reasons: candidates.append({"path": row["path"], "reasons": reasons})
    write_json(CLEAN / "build-manifest.json", {
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repository_commit": run(["git", "rev-parse", "HEAD"]).stdout.decode().strip(),
        "temporary_contexts_destroyed_after_build": True,
        "docker_build_no_cache": True,
        "source_context_is_repository_root": False,
        "node_parent": {"requested_tag": "node:18-alpine", "pinned_ref": node_ref,
                        "image_id": node["Id"], "repo_digests": node.get("RepoDigests", [])},
        "base": {"tag": BASE_TAG, "pinned_ref_for_child": base_pinned,
                 "pinned_ref_mode": "local content-address-named tag verified against exact image ID before build",
                 "docker_buildkit_limitation": "A local-only repo@sha256 reference triggered a registry pull; the derived tag embeds the full ID and was checked immediately before use.",
                 "context_files": base_files, **base_build},
        "poc": {"tag": POC_TAG, "context_files": poc_files, **poc_build},
        "clean_filesystem_entries": len(rows),
        "candidate_context_files": candidates,
        "project_string_hit_files": len(hits),
        "direct_api_used": False,
        "codex_subject_launched": False,
    })
    print(json.dumps({"base_image": base_build["image_id"],
                      "base_pinned": base_pinned,
                      "poc_image": poc_build["image_id"],
                      "filesystem_entries": len(rows),
                      "candidate_files": len(candidates),
                      "project_string_hit_files": len(hits)}, indent=2))


if __name__ == "__main__":
    main()
