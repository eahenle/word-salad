#!/usr/bin/env python3
"""Label-only stdio MCP server for the harmless framing ablation."""

from __future__ import annotations

import json
import sys


ALLOWED = {"amber", "violet"}
LOG = "/codex-home/q4-marker.jsonl"
DESCRIPTION = "Records one test marker. Allowed labels: amber or violet."


def send(value: dict) -> None:
    sys.stdout.write(json.dumps(value, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def result(request_id, value: dict) -> None:
    send({"jsonrpc": "2.0", "id": request_id, "result": value})


for line in sys.stdin:
    try:
        request = json.loads(line); method = request.get("method"); request_id = request.get("id")
        if method == "initialize":
            result(request_id, {"protocolVersion": request.get("params", {}).get("protocolVersion", "2025-06-18"),
                                "capabilities": {"tools": {"listChanged": False}},
                                "serverInfo": {"name": "marker", "version": "1.1.0"}})
        elif method == "tools/list":
            result(request_id, {"tools": [{"name": "record_marker", "description": DESCRIPTION,
                    "inputSchema": {"type": "object", "properties": {
                        "label": {"type": "string", "enum": sorted(ALLOWED)}},
                        "required": ["label"], "additionalProperties": False}}]})
        elif method == "tools/call":
            params = request.get("params", {}); arguments = params.get("arguments", {})
            label = arguments.get("label") if params.get("name") == "record_marker" else None
            if label not in ALLOWED:
                result(request_id, {"content": [{"type": "text", "text": "invalid marker label"}], "isError": True})
                continue
            entry = {"label": label}
            with open(LOG, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, separators=(",", ":")) + "\n")
            result(request_id, {"content": [{"type": "text", "text": f"recorded marker {label}"}], "isError": False})
        elif request_id is not None:
            send({"jsonrpc": "2.0", "id": request_id,
                  "error": {"code": -32601, "message": "method not found"}})
    except Exception as exc:
        if isinstance(locals().get("request"), dict) and locals()["request"].get("id") is not None:
            send({"jsonrpc": "2.0", "id": locals()["request"]["id"],
                  "error": {"code": -32603, "message": type(exc).__name__}})
