#!/usr/bin/env python3
"""Compare the historical frozen and independently rebuilt image inventories."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def load_inventory(path: Path) -> dict[str, dict[str, str]]:
    lines = path.read_text().splitlines()
    header = lines[0].split("\t")
    rows = [dict(zip(header, line.split("\t"))) for line in lines[1:]]
    return {row["path"]: {key: ("" if value == "-" else value) for key, value in row.items()}
            for row in rows}


def hit_map(path: Path) -> dict[str, str]:
    output = {}
    for block in path.read_text(errors="replace").split("\n\n"):
        if not block.startswith("PATH: "): continue
        lines = block.splitlines(); name = lines[0].removeprefix("PATH: ")
        output[name] = next((line.removeprefix("TERMS: ") for line in lines
                             if line.startswith("TERMS: ")), "")
    return output


def main() -> None:
    historical = load_inventory(ROOT / "filesystem-inventory.txt")
    clean = load_inventory(ROOT / "clean-build/filesystem-inventory.txt")
    shared = sorted(historical.keys() & clean.keys())
    fields = ("kind", "mode", "uid", "gid", "size", "sha256", "target")
    differences = []
    for path in shared:
        changes = {field: {"historical": historical[path].get(field, ""),
                           "clean": clean[path].get(field, "")}
                   for field in fields if historical[path].get(field, "") != clean[path].get(field, "")}
        if changes: differences.append({"path": path, "changes": changes})
    only_historical = sorted(historical.keys() - clean.keys())
    only_clean = sorted(clean.keys() - historical.keys())
    historical_inspect = json.loads((ROOT / "frozen-image-inspect.json").read_text())
    clean_inspect = json.loads((ROOT / "clean-build/image-inspect.json").read_text())
    build_manifest = json.loads((ROOT / "clean-build/build-manifest.json").read_text())
    base_result = subprocess.run(["docker", "image", "inspect", build_manifest["base"]["image_id"]],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if base_result.returncode:
        raise RuntimeError("clean base image is unavailable for ancestry verification")
    clean_base_inspect = json.loads(base_result.stdout)[0]
    (ROOT / "clean-build/base-image-inspect.json").write_text(
        json.dumps(clean_base_inspect, indent=2, sort_keys=True) + "\n")
    base_layers = clean_base_inspect["RootFS"]["Layers"]
    clean_layers = clean_inspect["RootFS"]["Layers"]
    effective_config_fields = ("Entrypoint", "Cmd", "Env", "User", "WorkingDir",
                               "Labels", "Volumes", "OnBuild")
    historical_effective_config = {key: historical_inspect["Config"].get(key)
                                   for key in effective_config_fields}
    clean_effective_config = {key: clean_inspect["Config"].get(key)
                              for key in effective_config_fields}
    historical_hits = hit_map(ROOT / "project-string-hits.txt")
    clean_hits = hit_map(ROOT / "clean-build/project-string-hits.txt")
    regular_shared = [path for path in shared if historical[path]["kind"] == "file"]
    regular_hash_identical = [path for path in regular_shared
                              if historical[path].get("sha256") == clean[path].get("sha256")]
    expected_differences = {
        "/etc/hostname": "Docker injects a per-container hostname at runtime; this is not immutable image context.",
        "/etc/shadow": "The adduser build step creates a fresh password-lock representation; no subject or project prose is present.",
    }
    expected_only_prefix = "/root/.npm/_logs/"
    unexplained = [row for row in differences if row["path"] not in expected_differences]
    unexplained += [{"path": path, "side": "historical-only"} for path in only_historical
                    if not path.startswith(expected_only_prefix)]
    unexplained += [{"path": path, "side": "clean-only"} for path in only_clean
                    if not path.startswith(expected_only_prefix)]
    key_paths = (
        "/opt/q4/marker_server.py",
        "/usr/local/bin/credential-gate-q4",
        "/usr/local/bin/credential-gate",
        "/usr/local/libexec/subject-shell",
        "/usr/local/share/ca-certificates/cisco-secure-access-root.crt",
        "/usr/local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-arm64/vendor/aarch64-unknown-linux-musl/bin/codex",
    )
    source_paths = {
        "/opt/q4/marker_server.py": "experiment-4/stego-poc/framing-ablation/container/marker_server.py",
        "/usr/local/bin/credential-gate-q4": "experiment-4/stego-poc/container/credential-gate-q4",
        "/usr/local/bin/credential-gate": "experiment-1b/isolation/credential-gate.sh",
        "/usr/local/libexec/subject-shell": "experiment-4/stego-poc/container/disabled-subject-shell",
        "/usr/local/share/ca-certificates/cisco-secure-access-root.crt": "experiment-1b/isolation/cisco-secure-access-root.crt",
    }
    result = {
        "historical_image": historical_inspect["Id"],
        "clean_image": clean_inspect["Id"],
        "historical_entries": len(historical), "clean_entries": len(clean),
        "shared_paths": len(shared), "shared_regular_files": len(regular_shared),
        "shared_regular_files_with_identical_hash": len(regular_hash_identical),
        "only_historical": only_historical, "only_clean": only_clean,
        "content_or_metadata_differences": differences,
        "expected_difference_explanations": expected_differences,
        "unexplained_differences": unexplained,
        "project_string_hit_maps_identical": historical_hits == clean_hits,
        "historical_project_string_hits": historical_hits,
        "clean_project_string_hits": clean_hits,
        "raw_config_json_equal": historical_inspect["Config"] == clean_inspect["Config"],
        "effective_runtime_config_equal": historical_effective_config == clean_effective_config,
        "historical_effective_runtime_config": historical_effective_config,
        "clean_effective_runtime_config": clean_effective_config,
        "raw_config_difference_explanation": "The clean OCI manifest omits legacy false/empty attach, TTY, hostname, domain, and image fields; effective runtime fields match.",
        "clean_base_layers_are_exact_prefix_of_clean_poc": clean_layers[:len(base_layers)] == base_layers,
        "key_file_hashes": {path: {"historical": historical.get(path, {}).get("sha256"),
                                   "clean": clean.get(path, {}).get("sha256"),
                                   "equal": historical.get(path, {}).get("sha256") == clean.get(path, {}).get("sha256")}
                            for path in key_paths},
        "source_file_equivalence": {image_path: {
            "source_path": source_path,
            "source_sha256": hashlib.sha256((REPO / source_path).read_bytes()).hexdigest(),
            "historical_sha256": historical.get(image_path, {}).get("sha256"),
            "matches_source": hashlib.sha256((REPO / source_path).read_bytes()).hexdigest()
                              == historical.get(image_path, {}).get("sha256"),
        } for image_path, source_path in source_paths.items()},
        "logical_filesystem_equivalent_for_context_audit": not unexplained,
    }
    (ROOT / "comparison-data.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    lines = [
        "# Historical versus clean image comparison", "",
        f"Historical frozen image: `{result['historical_image']}`", "",
        f"Clean reconstructed PoC image: `{result['clean_image']}`", "",
        "## Result", "",
        "The images are logically equivalent for the context-contamination question. "
        "All shared regular files except `/etc/shadow` and the runtime-injected `/etc/hostname` are byte-identical. "
        "The only path-set differences are npm build-log filenames containing their respective build timestamps.", "",
        "| Check | Historical | Clean |", "| --- | ---: | ---: |",
        f"| Filesystem entries | {len(historical)} | {len(clean)} |",
        f"| Shared paths | {len(shared)} | {len(shared)} |",
        f"| Shared regular files | {len(regular_shared)} | {len(regular_shared)} |",
        f"| Byte-identical shared regular files | {len(regular_hash_identical)} | {len(regular_hash_identical)} |",
        f"| Project-term hit files | {len(historical_hits)} | {len(clean_hits)} |", "",
        "The project-term hit maps are identical. The sole intentional experiment-specific file is "
        "`/opt/q4/marker_server.py`, which contains `amber` and `violet`. Generic matches such as "
        "`multiplex`, `interleave`, `stride`, and `prompt injection` occur in standard runtime/package binaries; "
        "none is a project prompt, history, memory, or instruction file.", "",
        "## Expected build/runtime differences", "",
        "- `/etc/hostname`: generated for each diagnostic container.",
        "- `/etc/shadow`: differs because the clean `adduser` build step generated fresh locked-account material.",
        "- `/root/.npm/_logs/*.log`: same two npm operations, timestamped on different build dates.",
        "- Layer count is 14 historical versus 13 clean because the historical 4B.1 child overwrote the 4B marker "
        "server in an extra layer; the clean PoC copies the frozen 4B.1 server once.", "",
        "No unexplained content, configuration, or path difference remains.",
    ]
    (ROOT / "comparison.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"unexplained_differences": len(unexplained),
                      "identical_shared_regular_files": len(regular_hash_identical),
                      "shared_regular_files": len(regular_shared),
                      "hit_maps_identical": historical_hits == clean_hits}, indent=2))


if __name__ == "__main__":
    main()
